import logging
import re
import time
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

SKIP_DOMAINS = {
    "google.com", "google.co.kr", "youtube.com", "facebook.com",
    "twitter.com", "instagram.com", "naver.com", "daum.net",
    "wikipedia.org", "tistory.com", "blog.naver.com",
}


def search_google(keyword: str, max_results: int = 15) -> list[dict]:
    """Search Google for businesses matching the keyword and extract contacts."""
    prospects = []
    encoded = quote_plus(keyword)
    url = f"https://www.google.com/search?q={encoded}&hl=ko&num=20"

    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=15) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                logger.warning(f"Google search returned {resp.status_code}")
                return prospects

            soup = BeautifulSoup(resp.text, "html.parser")

            # Extract links from search results
            seen_urls = set()
            for a_tag in soup.select("a[href]"):
                href = a_tag.get("href", "")
                if href.startswith("/url?q="):
                    actual_url = href.split("/url?q=")[1].split("&")[0]
                    if actual_url.startswith("http"):
                        parsed = urlparse(actual_url)
                        if not any(skip in parsed.netloc for skip in SKIP_DOMAINS):
                            seen_urls.add(actual_url)
                elif href.startswith("http"):
                    parsed = urlparse(href)
                    if not any(skip in parsed.netloc for skip in SKIP_DOMAINS):
                        seen_urls.add(href)

            # Visit each URL to extract contacts
            for site_url in list(seen_urls)[:max_results]:
                try:
                    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=10) as visit_client:
                        page_resp = visit_client.get(site_url)
                        if page_resp.status_code != 200:
                            continue

                        text = page_resp.text
                        emails = list(set(EMAIL_REGEX.findall(text)))
                        phones = list(set(PHONE_REGEX.findall(text)))

                        # Filter out common non-business emails
                        emails = [
                            e for e in emails
                            if not any(
                                d in e.lower()
                                for d in ["example.com", "test.com", "naver.com", "google.com"]
                            ) and len(e) < 100
                        ]

                        if emails or phones:
                            domain = urlparse(site_url).netloc
                            prospect = {
                                "name": domain,
                                "website": site_url,
                                "email": emails[0] if emails else None,
                                "phone": phones[0] if phones else None,
                                "source": "google",
                                "category": keyword,
                            }
                            prospects.append(prospect)

                    time.sleep(1.5)  # Rate limiting for Google
                except Exception as e:
                    logger.debug(f"Error processing {site_url}: {e}")
                    continue

    except Exception as e:
        logger.error(f"Google search error for '{keyword}': {e}")

    return prospects
