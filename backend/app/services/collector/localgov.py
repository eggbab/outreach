"""지자체 인허가(LOCALDATA) 수집기 — 오프라인 업소 커버용.

행정안전부가 전국 지자체의 인허가 업소(음식점·카페 등)를 공개한다.
사업장명·도로명주소·전화번호(사업장 유선)·영업상태가 나온다 — 정부
공개 데이터라 수집 리스크 0. 오프라인 가게(정부 등록부/통신판매에
없는 업체)를 메우는 채널.

키: localdata.go.kr 회원가입 → 인증키 신청 → LOCALDATA_API_KEY 환경변수.
키가 없거나 서버 접속이 안 되면 조용히 스킵한다.

⚠️ 상태(2026-08-29): localdata.go.kr 서버가 접속 불가(점검 추정)라
   실서버 검증을 못 했다. 업종코드는 문헌에서 교차확인된 것만 넣었고,
   서버 복구 후 실호출로 검증·확장해야 한다.
"""
import logging
import os

import httpx

logger = logging.getLogger(__name__)

API_URL = "http://www.localdata.go.kr/platform/rest/TO0/openDataApi"

# 키워드에 이 단어가 들어가면 해당 업종코드(opnSvcId)로 조회.
# 문헌에서 교차확인된 코드만 — 서버 복구 후 공식 코드표로 확장할 것.
KEYWORD_TO_SVC = {
    "음식점": "07_24_04_P",   # 일반음식점
    "식당": "07_24_04_P",
    "맛집": "07_24_04_P",
    "카페": "07_24_05_P",     # 휴게음식점
    "커피": "07_24_05_P",
    "디저트": "07_24_05_P",
    "분식": "07_24_05_P",
}

# 키워드의 지역어 → 시도 필터 (응답의 주소 필드로 클라이언트측 필터)
REGIONS = (
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
)


def _match_svc(keyword: str) -> str | None:
    for word, code in KEYWORD_TO_SVC.items():
        if word in keyword:
            return code
    return None


def _region_of(keyword: str) -> str | None:
    for r in REGIONS:
        if r in keyword:
            return r
    return None


def search_localgov(keyword: str, max_results: int = 20, match_level: str = "medium") -> list[dict]:
    api_key = os.getenv("LOCALDATA_API_KEY", "").strip()
    if not api_key:
        logger.info("[localgov] LOCALDATA_API_KEY 없음 — 인허가 수집 건너뜀")
        return []

    svc = _match_svc(keyword)
    if not svc:
        logger.info(f"[localgov] '{keyword}' 에 매핑된 인허가 업종 없음 — 건너뜀")
        return []
    region = _region_of(keyword)

    prospects: list[dict] = []
    try:
        with httpx.Client(timeout=20) as client:
            page = 1
            while len(prospects) < max_results and page <= 5:
                r = client.get(API_URL, params={
                    "authKey": api_key,
                    "opnSvcId": svc,
                    "state": "01",          # 영업중
                    "pageIndex": page,
                    "pageSize": 300,
                    "resultType": "json",
                })
                if r.status_code != 200:
                    logger.warning(f"[localgov] HTTP {r.status_code}")
                    return prospects
                body = r.json().get("result", {}).get("body", {})
                rows = body.get("rows", [])
                if isinstance(rows, list) and rows and isinstance(rows[0], dict) and "row" in rows[0]:
                    rows = rows[0]["row"]
                if not rows:
                    break
                for it in rows:
                    name = (it.get("bplcNm") or "").strip()       # 사업장명
                    addr = (it.get("rdnWhlAddr") or it.get("siteWhlAddr") or "").strip()
                    phone = (it.get("siteTel") or "").strip() or None
                    if not name or not phone:
                        continue
                    if region and region not in addr:
                        continue
                    prospects.append({
                        "name": name,
                        "email": None,
                        "phone": phone,
                        "instagram": None,
                        "website": None,
                        "source": "localgov",
                        "category": keyword,
                        "description": " · ".join(x for x in (
                            it.get("uptaeNm"), addr, "지자체 인허가 업소") if x) or None,
                    })
                    if len(prospects) >= max_results:
                        break
                page += 1
    except Exception as e:
        logger.warning(f"[localgov] 조회 실패 '{keyword}' (건너뜀): {e}")
        return prospects

    logger.info(f"[localgov] '{keyword}' → {len(prospects)}건 (인허가)")
    return prospects
