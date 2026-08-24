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
    encoded = quote_plus(keyword)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=USER_AGENT,
                locale="ko-KR",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            # Navigate to Naver Map to establish cookies/context, then fetch API
            page.goto("https://map.naver.com/", timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            # Use the internal API endpoint via page.evaluate (same-origin fetch)
            api_url = f"https://map.naver.com/p/api/search/allSearch?query={encoded}&type=all"
            result = page.evaluate(
                """async (url) => {
                    try {
                        const resp = await fetch(url, {
                            headers: { 'Accept': 'application/json' }
                        });
                        const text = await resp.text();
                        return { ok: resp.ok, status: resp.status, body: text };
                    } catch(e) {
                        return { ok: false, status: 0, body: String(e) };
                    }
                }""",
                api_url,
            )

            data = None
            if result and result.get("ok"):
                try:
                    import json as _json
                    data = _json.loads(result.get("body") or "")
                except Exception:
                    data = None

            if data is None:
                logger.warning(
                    f"[naver_map/search] API returned no data for '{keyword}' "
                    f"(status={result.get('status') if result else 'n/a'}, "
                    f"body_preview={(result.get('body') or '')[:120] if result else ''!r})"
                )
                browser.close()
                return prospects

            # Extract place results
            place_list = (
                data.get("result", {}).get("place", {}).get("list", [])
                if isinstance(data, dict)
                else []
            )

            for place in place_list:
                if len(prospects) >= max_results:
                    break
                place_name = place.get("name", "")
                place_phone = place.get("tel", "")
                website = place.get("homePage", "") or place.get("virtualPhone", "")

                email = None
                insta = None
                if website and website.startswith("http"):
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
