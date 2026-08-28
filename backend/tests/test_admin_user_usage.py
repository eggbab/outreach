"""관리자가 보는 '이 사용자가 얼마나 썼나' 집계."""
import pytest

from app.core.plans import add_credits, deduct_credits
from app.models.models import EmailLog, Project, Prospect, User


@pytest.fixture
def admin_headers(client, db_session, auth_headers):
    u = db_session.query(User).first()
    u.is_admin = True
    db_session.commit()
    return auth_headers


class TestUserUsage:
    def test_reports_zero_for_fresh_user(self, client, admin_headers, db_session):
        u = db_session.query(User).first()
        r = client.get(f"/api/admin/users/{u.id}/usage", headers=admin_headers)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["email"] == u.email
        assert d["emails_sent"] == 0
        assert d["dms_sent"] == 0

    def test_counts_prospects_and_emails(self, client, admin_headers, db_session, project_id):
        u = db_session.query(User).first()
        proj = db_session.query(Project).filter(Project.id == project_id).first()
        for i in range(3):
            db_session.add(Prospect(project_id=proj.id, name=f"업체{i}",
                                    email=f"c{i}@corp.com", status="approved"))
        db_session.flush()
        p = db_session.query(Prospect).first()
        db_session.add(EmailLog(prospect_id=p.id, user_id=u.id, status="success",
                                tracking_id="t-usage-1"))
        db_session.commit()

        d = client.get(f"/api/admin/users/{u.id}/usage", headers=admin_headers).json()
        assert d["prospect_count"] == 3
        assert d["emails_sent"] == 1
        assert d["project_count"] >= 1

    def test_separates_charged_and_spent(self, client, admin_headers, db_session):
        """충전과 사용을 나눠서 보여줘야 한다."""
        u = db_session.query(User).first()
        add_credits(db_session, u.id, 1000, "테스트 충전")
        deduct_credits(db_session, u.id, 300, "테스트 사용")
        db_session.commit()

        d = client.get(f"/api/admin/users/{u.id}/usage", headers=admin_headers).json()
        assert d["credits_purchased"] >= 1000
        assert d["credits_spent"] >= 300
        # 최근 내역이 새 것부터 내려와야 한다
        assert d["recent_transactions"][0]["description"] == "테스트 사용"

    def test_unknown_user_is_404(self, client, admin_headers):
        assert client.get("/api/admin/users/999999/usage", headers=admin_headers).status_code == 404

    def test_non_admin_blocked(self, client, auth_headers, db_session):
        u = db_session.query(User).first()
        u.is_admin = False
        db_session.commit()
        r = client.get(f"/api/admin/users/{u.id}/usage", headers=auth_headers)
        assert r.status_code in (401, 403)
