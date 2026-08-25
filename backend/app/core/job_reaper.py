"""고아 작업 정리 — 프로세스 재시작 시 'running'으로 멈춘 작업을 실패 처리.

수집/이메일 발송은 데몬 스레드로 도는데, 프로세스가 중간에 죽으면 스레드는 사라지지만
DB의 CollectionJob/EmailSendJob은 status='running'으로 영원히 남아
해당 프로젝트의 재수집을 영구 차단하고, 상태 폴링이 영원히 'running'을 반환한다.

시작 시 한 번 정리 + 스케줄러가 주기적으로 재확인(장시간 hang 방지).
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import update

logger = logging.getLogger(__name__)

# 이 시간을 넘겨 running인 작업은 죽은 것으로 간주 (정상 작업은 이보다 훨씬 빨리 끝남)
STALE_AFTER_MINUTES = 90


def reap_stale_jobs(db, *, startup: bool = False) -> int:
    """멈춘 running 작업을 failed로 정리. 정리한 건수 반환.

    startup=True면 시각 무관하게 모든 running을 정리(재시작 = 스레드 전멸이 확실).
    주기 실행 시엔 STALE_AFTER_MINUTES 초과분만 정리(진행 중인 정상 작업 보호).
    """
    from app.models.models import CollectionJob, EmailSendJob

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=STALE_AFTER_MINUTES)
    cutoff_naive = cutoff.replace(tzinfo=None)  # 컬럼이 naive-UTC
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)

    total = 0
    for model, msg in (
        (CollectionJob, "서버 재시작으로 중단됨 — 다시 시도해주세요"),
        (EmailSendJob, "서버 재시작으로 중단됨 — 다시 시도해주세요"),
    ):
        stmt = update(model).where(model.status == "running")
        if not startup:
            stmt = stmt.where(model.started_at < cutoff_naive)
        stmt = stmt.values(status="failed", error=msg, completed_at=now_naive)
        result = db.execute(stmt)
        total += result.rowcount or 0

    # 예약 발송인데 running으로 넘어가 멈춘 것도 위에서 처리됨.
    if total:
        db.commit()
        logger.info(f"job_reaper: 멈춘 작업 {total}건을 failed로 정리 (startup={startup})")
    return total
