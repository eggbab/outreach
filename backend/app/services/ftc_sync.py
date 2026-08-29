"""공정위 통신판매사업자 등록부를 로컬 DB로 미러링.

정부 API는 상호 검색이 안 되고(사업자번호 단건 + 전체 목록 페이징만),
전체가 270만 건이라 매 수집마다 훑을 수 없다. 그래서:
  - 최신 신고분부터 역순으로 최대 FTC_SYNC_MAX_ROWS 건을 받아 저장
  - 정상영업 + 연락처(이메일/전화/도메인) 보유 건만 (응답률 높은 데이터만)
  - 수집기는 이 미러에서 LIKE 검색

용량 주의: Supabase 무료 500MB 한도 때문에 기본 60만 건(약 150MB)으로 제한.
"""
import logging
import os
from datetime import timedelta

import httpx
from sqlalchemy.orm import Session

from app.models.models import FtcBusiness, utcnow

logger = logging.getLogger(__name__)

API_URL = "https://apis.data.go.kr/1130000/MllBsDtl_3Service/getMllBsInfoDetail_3"
PAGE_SIZE = 5000                       # 실측 상한 확인됨
DEFAULT_MAX_ROWS = 600_000             # 최근 신고분 기준 (약 2023년 이후 커버)
SYNC_INTERVAL_DAYS = 7                 # 이보다 어리면 재적재 생략


def _clean(v):
    v = (v or "").strip()
    return None if v in ("", "N/A", "NULL", "null") else v


def _clean_email(v):
    """마스킹된 이메일(abc**@x.com)은 발송 불가 — 버린다."""
    v = _clean(v)
    if not v or "**" in v or "@" not in v:
        return None
    return v


def _clean_phone(v):
    """'010-개인정보' 같은 마스킹 값 제거."""
    v = _clean(v)
    if not v or "개인정보" in v:
        return None
    digits = "".join(ch for ch in v if ch.isdigit())
    return v if len(digits) >= 8 else None


def _clean_website(v):
    """'http://네이버 스마트스토어' 같은 비URL 텍스트 제거."""
    v = _clean(v)
    if not v:
        return None
    u = v if v.startswith("http") else f"http://{v}"
    host = u.split("://", 1)[-1].split("/")[0]
    if " " in host or "." not in host:
        return None
    return u


def _total_pages(client: httpx.Client, api_key: str) -> tuple[int, int]:
    r = client.get(API_URL, params={
        "serviceKey": api_key, "resultType": "json", "pageNo": 1, "numOfRows": 1})
    total = int(r.json().get("totalCount", 0))
    return total, (total + PAGE_SIZE - 1) // PAGE_SIZE


def sync_ftc_registry(db: Session, max_rows: int | None = None, force: bool = False) -> dict:
    """등록부 미러 갱신. 반환: 진행 요약 dict."""
    api_key = os.getenv("DATA_GO_KR_API_KEY", "").strip()
    if not api_key:
        return {"status": "skipped", "reason": "DATA_GO_KR_API_KEY 없음"}

    # 최근에 동기화했으면 생략 (스케줄러가 매주 부르지만 이중 방어)
    newest = db.query(FtcBusiness.synced_at).order_by(
        FtcBusiness.synced_at.desc()).first()
    if newest and not force:
        if newest[0] > utcnow() - timedelta(days=SYNC_INTERVAL_DAYS - 1):
            return {"status": "fresh", "reason": "최근 동기화됨"}

    max_rows = max_rows or int(os.getenv("FTC_SYNC_MAX_ROWS", DEFAULT_MAX_ROWS))
    saved = scanned = 0
    try:
        with httpx.Client(timeout=90) as client:
            total, last_page = _total_pages(client, api_key)
            logger.info(f"[ftc_sync] 등록부 전체 {total:,}건 — 최신부터 최대 {max_rows:,}건 적재")

            # 목록이 신고일 오름차순이므로 마지막 페이지부터 역순으로
            page = last_page
            while page >= 1 and scanned < max_rows:
                r = client.get(API_URL, params={
                    "serviceKey": api_key, "resultType": "json",
                    "pageNo": page, "numOfRows": PAGE_SIZE})
                items = r.json().get("items") or []
                scanned += len(items)

                rows = []
                for it in items:
                    if it.get("operSttusCdNm") != "정상영업":
                        continue
                    email = _clean_email(it.get("rprsvEmladr"))
                    phone = _clean_phone(it.get("telno"))
                    website = _clean_website(it.get("domnCn"))
                    # 발송/방문 가능한 단서가 하나는 있어야 저장
                    if not (email or phone or website):
                        continue
                    brno = _clean(it.get("brno"))
                    name = _clean(it.get("bzmnNm"))
                    if not brno or not name:
                        continue
                    rows.append({
                        "brno": brno, "name": name[:200],
                        "email": email[:255] if email else None,
                        "phone": phone[:30] if phone else None,
                        "website": website[:300] if website else None,
                        "address": (_clean(it.get("lctnRnAddr")) or _clean(it.get("lctnAddr")) or "")[:300] or None,
                        "region": (_clean(it.get("ctpvNm")) or "")[:30] or None,
                        "product": (_clean(it.get("trtmntPrdlstNm")) or _clean(it.get("ntslPrdlstCn")) or "")[:300] or None,
                        "declared_date": _clean(it.get("dclrDate")),
                        "synced_at": utcnow(),
                    })

                if rows:
                    # 같은 페이지 안에 brno 중복이 있으면 upsert가 죽는다 — 마지막 것만
                    rows = list({r["brno"]: r for r in rows}.values())
                    # brno 충돌 시 갱신 (upsert) — DB 방언별 처리
                    if db.bind.dialect.name == "postgresql":
                        from sqlalchemy.dialects.postgresql import insert as pg_insert
                        stmt = pg_insert(FtcBusiness).values(rows)
                        stmt = stmt.on_conflict_do_update(
                            index_elements=[FtcBusiness.brno],
                            set_={c: stmt.excluded[c] for c in
                                  ("name", "email", "phone", "website", "address",
                                   "region", "product", "declared_date", "synced_at")})
                        db.execute(stmt)
                    else:  # sqlite (테스트)
                        for row in rows:
                            ex = db.query(FtcBusiness).filter(FtcBusiness.brno == row["brno"]).first()
                            if ex:
                                for k, v in row.items():
                                    setattr(ex, k, v)
                            else:
                                db.add(FtcBusiness(**row))
                    db.commit()
                    saved += len(rows)

                if page % 20 == 0:
                    logger.info(f"[ftc_sync] 진행 {scanned:,}건 스캔 / {saved:,}건 저장 (page {page})")
                page -= 1
    except Exception as e:
        logger.error(f"[ftc_sync] 적재 중단: {e} (지금까지 {saved:,}건 저장)")
        return {"status": "partial", "saved": saved, "scanned": scanned, "error": str(e)}

    logger.info(f"[ftc_sync] 완료 — {scanned:,}건 스캔, {saved:,}건 저장")
    return {"status": "completed", "saved": saved, "scanned": scanned}
