import logging
import random
import time
from urllib.parse import quote_plus, urlparse

from playwright.sync_api import sync_playwright
from app.services.collector.extract import deep_extract_email, keyword_matches

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _random_delay(min_sec: float = 1.0, max_sec: float = 3.0):
    """Sleep for a random duration between min_sec and max_sec."""
    time.sleep(random.uniform(min_sec, max_sec))


def search_naver(keyword: str, max_results: int = 20, match_level: str = "medium") -> list[dict]:
    """Search Naver web for businesses matching the keyword using Playwright."""
    prospects = []
    encoded = quote_plus(keyword)
    search_url = f"https://search.naver.com/search.naver?query={encoded}&where=web"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=USER_AGENT,
                locale="ko-KR",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            # Navigate to Naver search
            page.goto(search_url, timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            # Extract all outbound links from search results
            links = page.eval_on_selector_all(
                "a[href]",
                """elements => elements
                    .map(el => el.href)
                    .filter(href =>
                        href.startsWith('http') &&
                        !href.includes('naver.com') &&
                        !href.includes('search.naver')
                    )
                """,
            )
            seen_urls = list(dict.fromkeys(links))[:max_results]  # dedupe, preserve order

            # Visit each URL to deep-extract contacts
            for site_url in seen_urls:
                if len(prospects) >= max_results:
                    break
                try:
                    email, phone, name, insta = deep_extract_email(page, site_url)

                    # 정밀도 필터 — 페이지가 키워드와 일치하는지 확인
                    if email or insta:
                        try:
                            page_title = page.title() or ""
                            page_text = page.text_content("body") or ""
                        except Exception:
                            page_title, page_text = "", ""
                        if not keyword_matches(page_title, page_text, keyword, match_level):
                            logger.info(f"[naver] {site_url} 키워드 불일치 ({match_level}) — 스킵")
                            continue

                        prospects.append({
                            "name": name or urlparse(site_url).netloc,
                            "website": site_url,
                            "email": email,
                            "phone": phone,
                            "instagram": insta,
                            "source": "naver",
                            "category": keyword,
                        })

                    _random_delay(0.5, 1.5)
                except Exception as e:
                    logger.error(f"[naver/search] Error processing {site_url}: {e}")
                    continue

            browser.close()

    except Exception as e:
        logger.error(f"[naver/search] Search error for '{keyword}': {e}")

    return prospects


def search_naver_shopping(keyword: str, max_results: int = 15, match_level: str = "medium") -> list[dict]:
    """Search Naver Shopping for smartstore sellers using Playwright."""
    prospects = []
    encoded = quote_plus(keyword)
    search_url = f"https://search.shopping.naver.com/search/all?query={encoded}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=USER_AGENT,
                locale="ko-KR",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            # Navigate to Naver Shopping search
            page.goto(search_url, timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)  # shopping page is JS-heavy

            # Extract smartstore links
            store_links = page.eval_on_selector_all(
                "a[href*='smartstore.naver.com']",
                """elements => {
                    const stores = new Set();
                    elements.forEach(el => {
                        const href = el.href;
                        if (href.includes('smartstore.naver.com')) {
                            try {
                                const url = new URL(href);
                                const pathParts = url.pathname.split('/');
                                // Get store base: /storename
                                const storeName = pathParts[1] || '';
                                if (storeName) {
                                    stores.add(url.origin + '/' + storeName);
                                }
                            } catch(e) {}
                        }
                    });
                    return [...stores];
                }""",
            )

            unique_stores = list(dict.fromkeys(store_links))[:max_results]

            for store_url in unique_stores:
                if len(prospects) >= max_results:
                    break
                try:
                    email, phone, name, insta = deep_extract_email(page, store_url)
                    store_name = name or urlparse(store_url).path.strip("/").split("/")[0]

                    if not (email or insta):
                        continue

                    prospects.append({
                        "name": store_name or urlparse(store_url).netloc,
                        "website": store_url,
                        "email": email,
                        "phone": phone,
                        "instagram": insta,
                        "source": "naver_shopping",
                        "category": keyword,
                    })
                    _random_delay(0.5, 1.0)
                except Exception as e:
                    logger.error(f"[naver_shopping/search] Error processing {store_url}: {e}")
                    continue

            browser.close()

    except Exception as e:
        logger.error(f"[naver_shopping/search] Search error for '{keyword}': {e}")

    return prospects


def search_naver_map(keyword: str, max_results: int = 15, match_level: str = "medium") -> list[dict]:
    """Search Naver Map for local businesses using Playwright."""
    prospects = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=USER_AGENT,
                locale="ko-KR",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            # 직접 API 호출은 네이버 캡차 토큰(CE_EMPTY_TOKEN)에 막힘 —
            # 실제 검색 페이지를 열고 페이지 스스로 호출한 allSearch 응답을 가로챈다.
            from urllib.parse import quote as _quote
            captured = []

            def _on_response(resp):
                if "api/search/allSearch" in resp.url and resp.status == 200:
                    try:
                        captured.append(resp.json())
                    except Exception:
                        pass

            page.on("response", _on_response)
            page.goto(
                f"https://map.naver.com/p/search/{_quote(keyword)}",
                timeout=30000,
                wait_until="domcontentloaded",
            )
            page.wait_for_timeout(6000)

            place_list = []
            for data in captured:
                pl = (data.get("result") or {}).get("place")
                if isinstance(pl, dict) and pl.get("list"):
                    place_list = pl["list"]
                    break

            if not place_list:
                logger.warning(
                    f"[naver_map/search] no place results for '{keyword}' "
                    f"(captured {len(captured)} responses — 캡차/차단 가능성)"
                )
                browser.close()
                return prospects

            for place in place_list:
                if len(prospects) >= max_results:
                    break
                place_name = place.get("name", "")
                place_phone = place.get("tel", "")
                website = place.get("homePage", "") or place.get("virtualPhone", "")

                email = None
                insta = None
                if website and "instagram.com/" in website:
                    # 인스타 링크는 핸들만 직접 파싱 (페이지 방문은 차단 위험 + 이메일 없음)
                    from app.services.collector.extract import normalize_instagram
                    insta = normalize_instagram(website)
                elif website and website.startswith("http"):
                    try:
                        email, extracted_phone, _, insta = deep_extract_email(page, website)
                        place_phone = place_phone or extracted_phone
                        _random_delay(0.5, 1.0)
                    except Exception as e:
                        logger.warning(f"[naver_map/search] Failed to extract from {website}: {e}")

                if not (email or insta or place_phone):
                    continue

                prospects.append({
                    "name": place_name,
                    "website": website if website else None,
                    "email": email,
                    "phone": place_phone if place_phone else None,
                    "instagram": insta,
                    "source": "naver_map",
                    "category": keyword,
                })

            browser.close()

    except Exception as e:
        logger.error(f"[naver_map/search] Search error for '{keyword}': {e}")

    return prospects
