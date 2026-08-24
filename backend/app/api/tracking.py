import base64
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import EmailLog, GlobalProspect, Prospect
from app.services.compliance import record_unsubscribe
from app.services.scoring import calculate_score

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/t", tags=["tracking"])

# 1x1 transparent GIF pixel
TRANSPARENT_PIXEL = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


@router.get("/open/{tracking_id}")
def track_open(
    tracking_id: str,
    db: Session = Depends(get_db),
):
    """Record email open via tracking pixel. Returns a 1x1 transparent GIF."""
    try:
        log = db.query(EmailLog).filter(EmailLog.tracking_id == tracking_id).first()
        if log and log.opened_at is None:
            log.opened_at = datetime.now(timezone.utc)
            prospect = db.query(Prospect).filter(Prospect.id == log.prospect_id).first()
            if prospect:
                prospect.score = calculate_score(db, prospect)
                if prospect.global_prospect_id:
                    gp = db.query(GlobalProspect).filter(GlobalProspect.id == prospect.global_prospect_id).first()
                    if gp:
                        gp.times_opened += 1
                        # 열람 = 실존 + 활성 메일함 증거
                        gp.email_validity_score = max(gp.email_validity_score or 0.0, 0.8)
                        gp.last_verified_at = datetime.now(timezone.utc)
            db.commit()
    except Exception:
        logger.exception("Failed to record email open for tracking_id=%s", tracking_id)
        # Silently ignore — always return the pixel
    return Response(content=TRANSPARENT_PIXEL, media_type="image/gif")


@router.get("/click/{tracking_id}")
def track_click(
    tracking_id: str,
    url: str = Query(..., description="The original URL to redirect to"),
    db: Session = Depends(get_db),
):
    """Record link click and redirect to the original URL."""
    # Validate URL scheme to prevent open redirect (e.g. javascript:, data:)
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid redirect URL scheme")

    try:
        log = db.query(EmailLog).filter(EmailLog.tracking_id == tracking_id).first()
        if log and log.clicked_at is None:
            log.clicked_at = datetime.now(timezone.utc)
            prospect = db.query(Prospect).filter(Prospect.id == log.prospect_id).first()
            if prospect:
                prospect.score = calculate_score(db, prospect)
                if prospect.global_prospect_id:
                    gp = db.query(GlobalProspect).filter(GlobalProspect.id == prospect.global_prospect_id).first()
                    if gp:
                        gp.times_clicked += 1
                        gp.email_validity_score = max(gp.email_validity_score or 0.0, 0.95)
                        gp.last_verified_at = datetime.now(timezone.utc)
            db.commit()
    except Exception:
        logger.exception("Failed to record click for tracking_id=%s", tracking_id)
        # Silently ignore — always redirect
    return RedirectResponse(url=url, status_code=302)


_UNSUB_PAGE = """<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>수신거부</title>
<style>
body {{ font-family: -apple-system, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
       display: flex; justify-content: center; align-items: center; min-height: 100vh;
       margin: 0; background: #f7f7f8; color: #333; }}
.card {{ background: #fff; border-radius: 12px; padding: 40px; max-width: 420px;
         text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,.06); }}
button {{ background: #dc2626; color: #fff; border: 0; border-radius: 8px;
          padding: 12px 28px; font-size: 15px; cursor: pointer; }}
p {{ line-height: 1.7; color: #666; font-size: 14px; }}
</style></head>
<body><div class="card">{content}</div></body></html>"""


@router.get("/unsub/{tracking_id}", response_class=HTMLResponse)
def unsubscribe_page(tracking_id: str):
    """수신거부 확인 페이지 (인증 불필요 — 메일 수신자용)."""
    content = (
        "<h2>메일 수신거부</h2>"
        "<p>더 이상 이 발신자의 메일을 받지 않으시겠습니까?<br>"
        "수신거부 시 향후 메일이 발송되지 않습니다.</p>"
        f'<form method="post" action="/api/t/unsub/{tracking_id}">'
        '<button type="submit">수신거부</button></form>'
    )
    return HTMLResponse(_UNSUB_PAGE.format(content=content))


@router.post("/unsub/{tracking_id}", response_class=HTMLResponse)
def unsubscribe_confirm(tracking_id: str, db: Session = Depends(get_db)):
    """수신거부 처리 — 유저 블랙리스트 + 전역 수신거부 풀 등록.

    RFC 8058 One-Click(List-Unsubscribe-Post) POST도 이 경로로 들어온다.
    """
    try:
        found = record_unsubscribe(db, tracking_id)
        if found:
            db.commit()
    except Exception:
        logger.exception("Failed to process unsubscribe for tracking_id=%s", tracking_id)
        db.rollback()
        found = False

    if found:
        content = "<h2>수신거부 완료</h2><p>처리되었습니다. 더 이상 메일이 발송되지 않습니다.</p>"
    else:
        content = "<h2>처리 불가</h2><p>유효하지 않은 요청입니다. 이미 처리되었거나 만료된 링크일 수 있습니다.</p>"
    return HTMLResponse(_UNSUB_PAGE.format(content=content))
