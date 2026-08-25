"""고아 작업 정리 테스트."""
from datetime import datetime, timedelta, timezone

from app.core.job_reaper import reap_stale_jobs
from app.models.models import CollectionJob, EmailSendJob, Project, User


def _setup(db):
    u = User(email="r@x.com", name="r", password_hash="x", credits=10)
    db.add(u)
    db.flush()
    p = Project(user_id=u.id, name="P")
    db.add(p)
    db.flush()
    return u, p


class TestJobReaper:
    def test_startup_reaps_all_running(self, db_session):
        u, p = _setup(db_session)
        db_session.add(CollectionJob(project_id=p.id, user_id=u.id, status="running"))
        db_session.add(EmailSendJob(project_id=p.id, user_id=u.id, status="running"))
        db_session.commit()

        n = reap_stale_jobs(db_session, startup=True)
        assert n == 2
        assert db_session.query(CollectionJob).first().status == "failed"
        assert db_session.query(EmailSendJob).first().status == "failed"
        assert "재시작" in db_session.query(CollectionJob).first().error

    def test_periodic_only_reaps_stale(self, db_session):
        u, p = _setup(db_session)
        # 방금 시작한 작업 (정상 진행 중) — 건드리면 안 됨
        fresh = CollectionJob(project_id=p.id, user_id=u.id, status="running")
        # 2시간 전 시작한 작업 (죽은 것) — 정리 대상
        old = CollectionJob(project_id=p.id, user_id=u.id, status="running")
        db_session.add_all([fresh, old])
        db_session.flush()
        old.started_at = (datetime.now(timezone.utc) - timedelta(hours=2)).replace(tzinfo=None)
        db_session.commit()

        n = reap_stale_jobs(db_session, startup=False)
        assert n == 1
        db_session.refresh(fresh)
        db_session.refresh(old)
        assert fresh.status == "running"  # 보호됨
        assert old.status == "failed"     # 정리됨

    def test_completed_jobs_untouched(self, db_session):
        u, p = _setup(db_session)
        db_session.add(CollectionJob(project_id=p.id, user_id=u.id, status="completed"))
        db_session.commit()
        n = reap_stale_jobs(db_session, startup=True)
        assert n == 0
        assert db_session.query(CollectionJob).first().status == "completed"
