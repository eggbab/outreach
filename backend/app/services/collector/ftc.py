"""공정거래위원회 통신판매사업자 등록부 수집기 + 국세청 폐업 필터.

전자상거래법상 통신판매업자는 상호·대표자·전화·이메일·주소를 신고해야 하고,
공정위가 이를 공공데이터 API로 공개한다. 즉 여기서 얻는 이메일·전화는
'정부에 신고된 공개 정보'라 수집 리스크가 없다. 온라인으로 뭔가를 파는
업체(쇼핑몰·스마트스토어 등)는 거의 다 들어 있다.

DATA_GO_KR_API_KEY 환경변수가 없으면 조용히 스킵된다(카카오와 동일한 정책).
발급: data.go.kr 가입 → '통신판매사업자 등록현황 제공 조회 서비스' 활용신청(무료)
      → 같은 키로 '국세청 사업자등록정보 상태조회'도 활용신청.

주의: 포털 API의 응답 필드명이 버전에 따라 다를 수 있어 후보 키를 여럿 둔다.
"""
import logging
import os

import httpx

logger = logging.getLogger(__name__)

# 공정위 통신판매사업자 조회 (버전 갱신 시 여기만 수정)
FTC_URL = "https://apis.data.go.kr/1130000/MllBs_1Service/getMllBsPrmsnMgtNoInfo_1"
# 국세청 사업자 상태조회 (폐업 필터)
NTS_URL = "https://api.odcloud.kr/api/nts-businessman/v1/status"


def _first(d: dict, *keys):
    """응답 필드명이 스펙 버전마다 달라서 후보를 순서대로 찾는다."""
    for k in keys:
        v = d.get(k)
        if v not in (None, "", "null"):
            return str(v).strip()
    return None


def _parse_items(payload: dict) -> list[dict]:
    """공공데이터포털 표준 응답(response.body.items)에서 아이템 목록을 꺼낸다."""
    body = (payload.get("response") or {}).get("body") or payload.get("body") or payload
    items = body.get("items") or []
    if isinstance(items, dict):  # {"item": [...]} 형태도 있다
        items = items.get("item") or []
    if isinstance(items, dict):
        items = [items]
    return items


def filter_closed_businesses(biz_nos: list[str], api_key: str) -> set[str]:
    """국세청 상태조회로 '계속사업자'가 아닌 사업자번호를 골라낸다.

    폐업한 업체에 영업 메일을 보내는 낭비를 막는다. 실패 시 빈 set
    (= 아무도 거르지 않음)으로 안전하게 처리.
    """
    closed: set[str] = set()
    if not biz_nos:
        return closed
    try:
        nos = [n.replace("-", "") for n in biz_nos if n]
        with httpx.Client(timeout=10) as client:
            for i in range(0, len(nos), 100):  # API 한도: 1회 100건
                r = client.post(
                    NTS_URL, params={"serviceKey": api_key},
                    json={"b_no": nos[i:i + 100]},
                )
                if r.status_code != 200:
                    logger.warning(f"[ftc/nts] 상태조회 HTTP {r.status_code} — 필터 생략")
                    return set()
                for row in r.json().get("data", []):
                    # b_stt_cd: 01 계속사업자 / 02 휴업 / 03 폐업
                    if row.get("b_stt_cd") in ("02", "03"):
                        closed.add(row.get("b_no", ""))
    except Exception as e:
        logger.warning(f"[ftc/nts] 상태조회 실패 (필터 생략): {e}")
        return set()
    return closed


def search_ftc(keyword: str, max_results: int = 20, match_level: str = "medium") -> list[dict]:
    """상호에 키워드가 들어간 통신판매사업자를 조회한다."""
    api_key = os.getenv("DATA_GO_KR_API_KEY", "").strip()
    if not api_key:
        logger.info("[ftc] DATA_GO_KR_API_KEY 없음 — 정부 등록부 수집 건너뜀")
        return []

    prospects: list[dict] = []
    seen_brno: set[str] = set()

    # "강남 카페"처럼 지역+업종 키워드는 상호 검색에 그대로 안 맞을 수 있어
    # 전체 → 마지막 단어(업종어) 순으로 시도한다.
    terms = [keyword]
    parts = keyword.split()
    if len(parts) > 1:
        terms.append(parts[-1])

    try:
        with httpx.Client(timeout=15) as client:
            for term in terms:
                if len(prospects) >= max_results:
                    break
                r = client.get(FTC_URL, params={
                    "serviceKey": api_key,
                    "pageNo": 1,
                    "numOfRows": min(max_results * 2, 100),
                    "resultType": "json",
                    "bzmnNm": term,          # 상호 (부분일치)
                    "opnSvcNm": "",
                })
                if r.status_code != 200:
                    logger.warning(f"[ftc] HTTP {r.status_code} for '{term}'")
                    continue
                try:
                    payload = r.json()
                except Exception:
                    logger.warning(f"[ftc] JSON 아님 (키 미승인/파라미터 불일치 가능): {r.text[:200]}")
                    continue

                for it in _parse_items(payload):
                    name = _first(it, "bzmnNm", "coNm", "corpNm", "상호")
                    if not name:
                        continue
                    brno = _first(it, "brno", "bizrno", "사업자등록번호")
                    if brno and brno in seen_brno:
                        continue
                    # 영업상태가 있으면 정상 영업만
                    status = _first(it, "operSttusCdNm", "bsnSttusNm", "업소상태") or ""
                    if status and any(x in status for x in ("폐업", "휴업", "직권말소")):
                        continue
                    email = _first(it, "email", "emailAdres", "전자우편")
                    phone = _first(it, "telno", "telNo", "전화번호")
                    domain = _first(it, "domnNm", "intnetDomnNm", "인터넷도메인")
                    addr = _first(it, "rnAddr", "lctnRnAddr", "사업장소재지(도로명)",
                                  "lctnAddr", "사업장소재지")
                    rep = _first(it, "rprsvNm", "대표자명")
                    if not (email or phone):
                        continue
                    if brno:
                        seen_brno.add(brno)
                    website = None
                    if domain:
                        website = domain if domain.startswith("http") else f"http://{domain}"
                    desc_bits = [b for b in (f"대표 {rep}" if rep else None, addr,
                                             "통신판매업 신고 업체") if b]
                    prospects.append({
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "instagram": None,
                        "website": website,
                        "source": "ftc",
                        "category": keyword,
                        "description": " · ".join(desc_bits) or None,
                        "biz_no": brno,
                    })
                    if len(prospects) >= max_results:
                        break
    except Exception as e:
        logger.error(f"[ftc] 조회 실패 '{keyword}': {e}")
        return prospects

    # 국세청 상태조회로 휴·폐업 걸러내기 (같은 키 사용)
    closed = filter_closed_businesses(
        [p["biz_no"] for p in prospects if p.get("biz_no")], api_key)
    if closed:
        before = len(prospects)
        prospects = [
            p for p in prospects
            if not (p.get("biz_no") and p["biz_no"].replace("-", "") in closed)
        ]
        logger.info(f"[ftc] 휴·폐업 {before - len(prospects)}건 제외")

    logger.info(f"[ftc] '{keyword}' → {len(prospects)}건 (정부 등록부)")
    return prospects
