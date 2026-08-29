"""
인스타그램 DM 라우트 — 크롬 확장 전용.

흐름:
1. 사용자가 크롬 확장을 설치하고 본인 인스타에 로그인 + 우리 서비스에 로그인.
2. 확장이 주기적으로 /dm/ping 으로 살아있음을 알림.
3. 확장이 /dm/queue 로 발송할 잠재고객 목록을 받음.
4. 확장이 사용자 본인 브라우저에서 인스타에 직접 fetch → DM 전송.
5. 발송 결과를 /chrome/dm-result (chrome.py) 또는 여기 /dm/log 폴링으로 확인.

서버는 발송 자체를 절대 수행하지 않음 — 크레딧 차감만 chrome/dm-result에서 처리.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import DmLog, Project, Prospect, User

router = APIRouter(
    prefix="/api/projects/{project_id}/dm",
    tags=["dm"],
)


def _verify_project(project_id: int, user_id: int, db: Session) -> None:
    """프로젝트 소유 확인 — IDOR(교차 테넌트 접근) 방지."""
    owned = (
        db.query(Project.id)
        .filter(Project.id == project_id, Project.user_id == user_id)
        .first()
    )
    if not owned:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

# 확장의 최근 ping 기록 (in-memory)
_extension_pings: dict[int, datetime] = {}


class DmStatusResponse(BaseModel):
    connected: bool
    last_ping_at: Optional[str] = None


class DmQueueItem(BaseModel):
    prospect_id: int
    name: Optional[str] = None
    instagram: str
    category: Optional[str] = None

    model_config = {"from_attributes": True}


class DmLogItem(BaseModel):
    prospect_id: int
    name: Optional[str] = None
    instagram: Optional[str] = None
    status: str
    sent_at: datetime
    error_message: Optional[str] = None


@router.get("/status", response_model=DmStatusResponse)
def get_dm_status(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """크롬 확장이 최근 5분 안에 ping을 보냈는지 확인."""
    last_ping = _extension_pings.get(current_user.id)
    connected = (
        last_ping is not None
        and (datetime.now(timezone.utc) - last_ping) < timedelta(minutes=5)
    )
    return DmStatusResponse(
        connected=connected,
        last_ping_at=last_ping.isoformat() if last_ping else None,
    )


@router.post("/ping")
def ping_extension(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """크롬 확장이 살아있음을 서버에 알림 (확장이 1분마다 호출)."""
    _extension_pings[current_user.id] = datetime.now(timezone.utc)
    return {"status": "ok"}


@router.get("/queue", response_model=list[DmQueueItem])
def get_dm_queue(
    project_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """승인됐고 인스타 핸들이 있고 아직 DM 안 보낸 잠재고객 (대시보드 표시용)."""
    _verify_project(project_id, current_user.id, db)
    from sqlalchemy import select
    dm_sent_ids = select(DmLog.prospect_id).where(
        DmLog.user_id == current_user.id, DmLog.status == "success"
    )

    prospects = (
        db.query(Prospect)
        .filter(
            Prospect.project_id == project_id,
            Prospect.status.in_(["approved", "email_sent"]),
            Prospect.instagram.isnot(None),
            Prospect.instagram != "",
            ~Prospect.id.in_(dm_sent_ids),
        )
        .order_by(Prospect.collected_at)
        .limit(limit)
        .all()
    )

    return [
        DmQueueItem(
            prospect_id=p.id, name=p.name, instagram=p.instagram, category=p.category,
        )
        for p in prospects
    ]


@router.get("/log", response_model=list[DmLogItem])
def get_dm_log(
    project_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """이 프로젝트의 DM 발송 기록."""
    _verify_project(project_id, current_user.id, db)
    logs = (
        db.query(DmLog, Prospect)
        .join(Prospect, DmLog.prospect_id == Prospect.id)
        .filter(Prospect.project_id == project_id, DmLog.user_id == current_user.id)
        .order_by(DmLog.sent_at.desc())
        .limit(limit)
        .all()
    )
    return [
        DmLogItem(
            prospect_id=log.prospect_id, name=prospect.name,
            instagram=prospect.instagram, status=log.status,
            sent_at=log.sent_at, error_message=log.error_message,
        )
        for log, prospect in logs
    ]


# ──────────────────────────────────────
# 인스타그램 확장 수집 요청 (프로젝트 화면 → 확장이 처리)
# ──────────────────────────────────────

class InstaCollectStartRequest(BaseModel):
    keyword: str
    target_count: int = 20


@router.post("/insta-collect")
def start_insta_collect(
    project_id: int,
    req: InstaCollectStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """인스타 수집 요청을 큐에 등록. 크롬 확장이 폴링해 사용자 브라우저에서 수행."""
    from app.models.models import InstaCollectJob
    _verify_project(project_id, current_user.id, db)

    keyword = (req.keyword or "").strip().lstrip("#")
    if not keyword:
        raise HTTPException(status_code=400, detail="검색어(해시태그)를 입력하세요")

    # 이미 대기/진행 중인 게 있으면 재사용 (중복 큐 방지)
    existing = (
        db.query(InstaCollectJob)
        .filter(
            InstaCollectJob.project_id == project_id,
            InstaCollectJob.status.in_(("pending", "running")),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="이미 진행 중인 인스타 수집이 있습니다")

    job = InstaCollectJob(
        project_id=project_id, user_id=current_user.id,
        keyword=keyword, target_count=max(1, min(req.target_count, 50)),
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"job_id": job.id, "keyword": keyword, "status": "pending"}


@router.get("/insta-collect/status")
def insta_collect_status(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """최근 인스타 수집 요청 상태."""
    from app.models.models import InstaCollectJob
    _verify_project(project_id, current_user.id, db)
    job = (
        db.query(InstaCollectJob)
        .filter(InstaCollectJob.project_id == project_id)
        .order_by(InstaCollectJob.created_at.desc())
        .first()
    )
    if not job:
        return {"status": "idle"}
    return {
        "status": job.status, "keyword": job.keyword,
        "found": job.found, "target": job.target_count, "message": job.message,
    }
