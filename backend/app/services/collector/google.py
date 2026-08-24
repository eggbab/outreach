import logging
import random
import time
from urllib.parse import quote_plus, urlparse

from playwright.sync_api import sync_playwright
from app.services.collector.extract import deep_extract_email, keyword_matches

logger = logging.getLogger(__name__)

SKIP_DOMAINS = {
    "google.com", "google.co.kr", "youtube.com", "facebook.com",
    "twitter.com", "instagram.com", "naver.com", "daum.net",
    "wikipedia.org", "tistory.com", "blog.naver.com", "linkedin.com",
}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _random_delay(min_sec: float = 1.0, max_sec: float = 3.0):
    """Sleep for a random duration between min_sec and max_sec."""
    time.sleep(random.uniform(min_sec, max_sec))


def search_google(keyword: str, max_results: int = 15, match_level: str = "medium") -> list[dict]:
    """Search Google for businesses matching the keyword and extract contacts using Playwright."""
    prospects = []
    encoded = quote_plus(keyword)
    search_url = f"https://www.google.com/search?q={encoded}&hl=ko&num=20"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=USER_AGENT,
                locale="ko-KR",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            # Navigate to Google search
            page.goto(search_url, timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            # Extract search result links, filtering out Google internal and skip domains
            skip_list = list(SKIP_DOMAINS)
            links = page.evaluate(
                """(skipDomains) => {
                    const results = new Set();
                    document.querySelectorAll('a[href]').forEach(a => {
                        let href = a.href;
                        // Handle Google redirect URLs
                        if (href.includes('/url?q=')) {
                            try {
                                const url = new URL(href);
                                href = url.searchParams.get('q') || href;
                            } catch(e) {}
                        }
                        if (!href.startsWith('http')) return;
                        try {
                            const hostname = new URL(href).hostname;
                            const dominated = skipDomains.some(d => hostname.includes(d));
                            if (!dominated) results.add(href);
                        } catch(e) {}
                    });
                    return [...results];
                }""",
                skip_list,
            )

            seen_urls = list(dict.fromkeys(links))[:max_results]

            # Visit each URL to deep-extract contacts
            for site_url in seen_urls:
                if len(prospects) >= max_results:
                    break
                try:
                    email, phone, name, insta = deep_extract_email(page, site_url)

                    if email or insta:
                        try:
                            page_title = page.title() or ""
                            page_text = page.text_content("body") or ""
                        except Exception:
                            page_title, page_text = "", ""
                        if not keyword_matches(page_title, page_text, keyword, match_level):
                            logger.info(f"[google] {site_url} 키워드 불일치 ({match_level}) — 스킵")
                            continue

                        prospects.append({
                            "name": name or urlparse(site_url).netloc,
                            "website": site_url,
                            "email": email,
                            "phone": phone,
                            "instagram": insta,
                            "source": "google",
                            "category": keyword,
                        })

                    _random_delay(0.5, 1.5)
                except Exception as e:
                    logger.error(f"[google/visit] Error processing {site_url}: {e}")
                    continue

            browser.close()

    except Exception as e:
        logger.error(f"[google/search] Search error for '{keyword}': {e}")

    return prospects
