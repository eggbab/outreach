import logging
import re
import time
from typing import Optional
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

MAX_RETRIES = 2
BACKOFF_SECONDS = [2, 4]


def _request_with_retry(client: httpx.Client, url: str, context: str = "") -> Optional[httpx.Response]:
    """
    Make an HTTP GET request with retry logic.
    - Retries up to 2 times with exponential backoff (2s, 4s).
    - On 403/429: sleep 5s and retry once.
    - On 404: skip silently, return None.
    - On timeout: log warning, return None.
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = client.get(url)

            if resp.status_code == 404:
                return None

            if resp.status_code in (403, 429):
                logger.warning(f"[{context}] HTTP {resp.status_code} (rate limited/blocked) for {url}")
                if attempt == 0:
                    time.sleep(5)
                    continue
                return None

            if resp.status_code != 200:
                logger.warning(f"[{context}] HTTP {resp.status_code} for {url}")
                if attempt < MAX_RETRIES:
                    time.sleep(BACKOFF_SECONDS[attempt])
                    continue
                return None

            return resp

        except httpx.TimeoutException:
            logger.warning(f"[{context}] Connection timeout for {url} (attempt {attempt + 1}/{MAX_RETRIES + 1})")
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_SECONDS[attempt])
                continue
            return None

        except httpx.ConnectError as e:
            logger.warning(f"[{context}] Connection error for {url}: {e} (attempt {attempt + 1}/{MAX_RETRIES + 1})")
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_SECONDS[attempt])
                continue
            return None

        except Exception as e:
            logger.error(f"[{context}] Unexpected error requesting {url}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_SECONDS[attempt])
                continue
            return None

    return None


def search_google(keyword: str, max_results: int = 15) -> list[dict]:
    """Search Google for businesses matching the keyword and extract contacts."""
    prospects = []
    encoded = quote_plus(keyword)
    url = f"https://www.google.com/search?q={encoded}&hl=ko&num=20"

    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=15) as client:
            resp = _request_with_retry(client, url, context="google/search")
            if resp is None:
                logger.warning(f"[google/search] Failed to get search results for '{keyword}'")
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
                        page_resp = _request_with_retry(visit_client, site_url, context="google/visit")
                        if page_resp is None:
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
                    logger.error(f"[google/visit] Error processing {site_url}: {e}")
                    continue

    except Exception as e:
        logger.error(f"[google/search] Search error for '{keyword}': {e}")

    return prospects
