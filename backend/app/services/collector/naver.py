import logging
import re
import time
from typing import Optional
from urllib.parse import quote_plus, urljoin, urlparse

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

# Exclude common non-business email domains
EXCLUDE_EMAIL_DOMAINS = {
    "example.com", "test.com", "naver.com", "google.com",
    "daum.net", "hanmail.net", "nate.com",
}


def _extract_contact_from_url(url: str, timeout: float = 10.0) -> dict:
    """Visit a URL and extract email/phone from page content."""
    result = {"emails": [], "phones": []}
    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=timeout) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return result

            text = resp.text

            # Extract emails
            emails = EMAIL_REGEX.findall(text)
            for email in emails:
                domain = email.split("@")[1].lower()
                if domain not in EXCLUDE_EMAIL_DOMAINS and len(email) < 100:
                    result["emails"].append(email.lower())

            # Extract phones
            phones = PHONE_REGEX.findall(text)
            result["phones"] = list(set(phones))

    except Exception as e:
        logger.debug(f"Error extracting contacts from {url}: {e}")

    result["emails"] = list(set(result["emails"]))
    return result


def search_naver(keyword: str, max_results: int = 20) -> list[dict]:
    """Search Naver web for businesses matching the keyword."""
    prospects = []
    encoded = quote_plus(keyword)
    url = f"https://search.naver.com/search.naver?query={encoded}&where=web"

    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=15) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                logger.warning(f"Naver search returned {resp.status_code}")
                return prospects

            soup = BeautifulSoup(resp.text, "html.parser")

            # Extract links from search results
            seen_urls = set()
            links = soup.select("a[href]")
            for link in links:
                href = link.get("href", "")
                if not href or "naver.com" in href or "search.naver" in href:
                    continue
                if href.startswith("http") and href not in seen_urls:
                    seen_urls.add(href)

            # Visit each URL to extract contacts
            for site_url in list(seen_urls)[:max_results]:
                try:
                    parsed = urlparse(site_url)
                    domain = parsed.netloc
                    contacts = _extract_contact_from_url(site_url)

                    if contacts["emails"] or contacts["phones"]:
                        prospect = {
                            "name": domain,
                            "website": site_url,
                            "email": contacts["emails"][0] if contacts["emails"] else None,
                            "phone": contacts["phones"][0] if contacts["phones"] else None,
                            "source": "naver",
                            "category": keyword,
                        }
                        prospects.append(prospect)

                    time.sleep(1)  # Rate limiting
                except Exception as e:
                    logger.debug(f"Error processing {site_url}: {e}")
                    continue

    except Exception as e:
        logger.error(f"Naver search error for '{keyword}': {e}")

    return prospects


def search_naver_shopping(keyword: str, max_results: int = 15) -> list[dict]:
    """Search Naver Shopping for smartstore sellers."""
    prospects = []
    encoded = quote_plus(keyword)
    url = f"https://search.shopping.naver.com/search/all?query={encoded}"

    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=15) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return prospects

            soup = BeautifulSoup(resp.text, "html.parser")

            # Look for smartstore links
            store_links = set()
            for a_tag in soup.select("a[href*='smartstore.naver.com']"):
                href = a_tag.get("href", "")
                if "smartstore.naver.com" in href:
                    # Extract the store base URL
                    parsed = urlparse(href)
                    store_base = f"{parsed.scheme}://{parsed.netloc}{parsed.path.split('/products')[0]}"
                    store_links.add(store_base)

            for store_url in list(store_links)[:max_results]:
                try:
                    contacts = _extract_contact_from_url(store_url)
                    store_name = urlparse(store_url).path.strip("/").split("/")[0] if "/" in urlparse(store_url).path else urlparse(store_url).netloc

                    prospect = {
                        "name": store_name,
                        "website": store_url,
                        "email": contacts["emails"][0] if contacts["emails"] else None,
                        "phone": contacts["phones"][0] if contacts["phones"] else None,
                        "source": "naver_shopping",
                        "category": keyword,
                    }
                    prospects.append(prospect)
                    time.sleep(1)
                except Exception:
                    continue

    except Exception as e:
        logger.error(f"Naver Shopping search error for '{keyword}': {e}")

    return prospects


def search_naver_map(keyword: str, max_results: int = 15) -> list[dict]:
    """Search Naver Map for local businesses."""
    prospects = []
    encoded = quote_plus(keyword)

    # Naver Map search API (public, no auth required)
    url = f"https://map.naver.com/p/api/search/allSearch?query={encoded}&type=all"

    try:
        map_headers = {**HEADERS, "Referer": "https://map.naver.com/"}
        with httpx.Client(headers=map_headers, follow_redirects=True, timeout=15) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return prospects

            try:
                data = resp.json()
            except Exception:
                return prospects

            # Extract place results
            place_list = data.get("result", {}).get("place", {}).get("list", [])

            for place in place_list[:max_results]:
                name = place.get("name", "")
                phone = place.get("tel", "")
                website = place.get("homePage", "") or place.get("virtualPhone", "")

                email = None
                # Try to extract email from the business website
                if website and website.startswith("http"):
                    contacts = _extract_contact_from_url(website)
                    email = contacts["emails"][0] if contacts["emails"] else None
                    time.sleep(0.5)

                prospect = {
                    "name": name,
                    "website": website if website else None,
                    "email": email,
                    "phone": phone if phone else None,
                    "source": "naver_map",
                    "category": keyword,
                }
                prospects.append(prospect)

    except Exception as e:
        logger.error(f"Naver Map search error for '{keyword}': {e}")

    return prospects
