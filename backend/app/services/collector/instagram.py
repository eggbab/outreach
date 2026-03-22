import logging
import re
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "X-IG-App-ID": "936619743392459",
}

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

MAX_RETRIES = 2
BACKOFF_SECONDS = [2, 4]


def _request_with_retry(client: httpx.Client, url: str, context: str = "", **kwargs) -> Optional[httpx.Response]:
    """
    Make an HTTP GET request with retry logic.
    - Retries up to 2 times with exponential backoff (2s, 4s).
    - On 403/429: sleep 5s and retry once.
    - On 404: skip silently, return None.
    - On timeout: log warning, return None.
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = client.get(url, **kwargs)

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


def search_instagram(keyword: str, max_results: int = 10) -> list[dict]:
    """
    Search Instagram for business profiles related to the keyword.

    This uses the public web search endpoint. For production use,
    consider using the Instagram Graph API with proper authentication.
    """
    prospects = []

    try:
        # Use Instagram's web search API
        url = "https://www.instagram.com/web/search/topsearch/"
        params = {"query": keyword}

        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=15) as client:
            resp = _request_with_retry(client, url, context="instagram/search", params=params)
            if resp is None:
                logger.warning(f"[instagram/search] Failed to get search results for '{keyword}'")
                return prospects

            try:
                data = resp.json()
            except Exception:
                logger.warning(f"[instagram/search] Invalid JSON response for '{keyword}'")
                return prospects

            users = data.get("users", [])
            for user_data in users[:max_results]:
                user = user_data.get("user", {})
                username = user.get("username", "")
                full_name = user.get("full_name", "")
                is_business = user.get("is_business", False)
                biography = user.get("biography", "")

                if not username:
                    continue

                # Try to extract email from biography
                email = None
                if biography:
                    emails = EMAIL_REGEX.findall(biography)
                    email = emails[0] if emails else None

                prospect = {
                    "name": full_name or username,
                    "instagram": username,
                    "email": email,
                    "phone": None,
                    "website": f"https://www.instagram.com/{username}/",
                    "source": "instagram",
                    "category": keyword,
                }
                prospects.append(prospect)

                time.sleep(0.5)

    except Exception as e:
        logger.error(f"[instagram/search] Search error for '{keyword}': {e}")

    return prospects


def get_profile_info(username: str) -> Optional[dict]:
    """
    Get detailed profile info for an Instagram user.
    Returns email, phone, website if available in bio.
    """
    try:
        url = f"https://www.instagram.com/{username}/?__a=1&__d=dis"

        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=10) as client:
            resp = _request_with_retry(client, url, context="instagram/profile")
            if resp is None:
                logger.warning(f"[instagram/profile] Failed to get profile for '{username}'")
                return None

            try:
                data = resp.json()
            except Exception:
                logger.warning(f"[instagram/profile] Invalid JSON response for '{username}'")
                return None

            user = data.get("graphql", {}).get("user", {})

            biography = user.get("biography", "")
            external_url = user.get("external_url", "")

            email = None
            if biography:
                emails = EMAIL_REGEX.findall(biography)
                email = emails[0] if emails else None

            return {
                "username": username,
                "full_name": user.get("full_name", ""),
                "biography": biography,
                "external_url": external_url,
                "email": email,
                "is_business": user.get("is_business_account", False),
                "follower_count": user.get("edge_followed_by", {}).get("count", 0),
            }

    except Exception as e:
        logger.error(f"[instagram/profile] Error getting profile for {username}: {e}")
        return None
