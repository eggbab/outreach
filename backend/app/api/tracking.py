import base64
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import EmailLog

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
            db.commit()
    except Exception:
        logger.exception("Failed to record click for tracking_id=%s", tracking_id)
        # Silently ignore — always redirect
    return RedirectResponse(url=url, status_code=302)
