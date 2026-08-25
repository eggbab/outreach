"""카카오 로컬 API 수집기 — 공식 REST API (키워드 장소 검색).

스크래핑과 달리 차단·캡차 리스크가 없는 합법 채널.
무료 쿼터: 일 10만 건 (developers.kakao.com 앱 등록 후 REST API 키 발급).
KAKAO_REST_API_KEY 환경변수가 없으면 조용히 스킵된다.

제공 필드: 상호명, 전화번호, 주소, 업종(카테고리), 카카오 플레이스 URL.
이메일은 없음 — 전화번호 기반 잠재고객으로 저장되고,
같은 업체가 네이버/구글에서 이메일과 함께 수집되면 dedup 단계에서 병합된다.
"""
import logging
import os

import httpx

logger = logging.getLogger(__name__)

KAKAO_API_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
PAGE_SIZE = 15
MAX_PAGES = 3  # 카카오 로컬 검색은 최대 45건


def search_kakao(keyword: str, max_results: int = 15, match_level: str = "medium") -> list[dict]:
    """카카오 로컬 키워드 검색. API 키 미설정 시 빈 목록."""
    api_key = os.getenv("KAKAO_REST_API_KEY", "").strip()
    if not api_key:
        return []

    prospects = []
    headers = {"Authorization": f"KakaoAK {api_key}"}

    try:
        with httpx.Client(timeout=10) as client:
            for page in range(1, MAX_PAGES + 1):
                if len(prospects) >= max_results:
                    break
                resp = client.get(
                    KAKAO_API_URL,
                    headers=headers,
                    params={"query": keyword, "page": page, "size": PAGE_SIZE},
                )
                if resp.status_code == 401:
                    logger.warning("[kakao] API 키가 유효하지 않습니다 (401)")
                    break
                if resp.status_code == 429:
                    logger.warning("[kakao] 일일 쿼터 초과 (429)")
                    break
                resp.raise_for_status()
                data = resp.json()

                for doc in data.get("documents", []):
                    if len(prospects) >= max_results:
                        break
                    name = (doc.get("place_name") or "").strip()
                    phone = (doc.get("phone") or "").strip()
                    if not name or not phone:
                        # 이메일/인스타 없이 전화도 없으면 잠재고객 가치 없음
                        continue
                    # category_name: "음식점 > 카페 > 커피전문점" → 마지막(가장 구체) 세그먼트
                    category_full = (doc.get("category_name") or "").strip()
                    category = category_full.split(">")[-1].strip() if category_full else keyword
                    # place_url은 카카오맵 링크(업체 홈페이지 아님) — 발송엔 무의미하나 업체 확인용
                    prospects.append({
                        "name": name,
                        "phone": phone,
                        "email": None,
                        "instagram": None,
                        "website": doc.get("place_url") or None,
                        "source": "kakao",
                        "category": category or keyword,
                        "address": doc.get("road_address_name") or doc.get("address_name") or None,
                    })

                if data.get("meta", {}).get("is_end", True):
                    break

    except Exception as e:
        logger.error(f"[kakao] Search error for '{keyword}': {e}")

    logger.info(f"[kakao] '{keyword}' → {len(prospects)}건")
    return prospects
