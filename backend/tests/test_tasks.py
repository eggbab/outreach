"""영업 할 일(태스크) CRUD + 리마인더 테스트."""
from datetime import datetime, timedelta, timezone


class TestTaskCRUD:
    def test_create_and_list(self, client, auth_headers):
        r = client.post("/api/tasks/", headers=auth_headers, json={"title": "A사 후속 전화"})
        assert r.status_code == 201
        tid = r.json()["id"]
        assert r.json()["done"] is False

        lst = client.get("/api/tasks/", headers=auth_headers)
        assert lst.status_code == 200
        assert any(t["id"] == tid for t in lst.json())

    def test_create_requires_title(self, client, auth_headers):
        assert client.post("/api/tasks/", headers=auth_headers, json={"title": "  "}).status_code == 400

    def test_complete_task(self, client, auth_headers):
        tid = client.post("/api/tasks/", headers=auth_headers, json={"title": "완료할 일"}).json()["id"]
        r = client.patch(f"/api/tasks/{tid}", headers=auth_headers, json={"done": True})
        assert r.status_code == 200 and r.json()["done"] is True
        # done=True 필터
        done_list = client.get("/api/tasks/?done=true", headers=auth_headers)
        assert any(t["id"] == tid for t in done_list.json())

    def test_delete_task(self, client, auth_headers):
        tid = client.post("/api/tasks/", headers=auth_headers, json={"title": "삭제할 일"}).json()["id"]
        assert client.delete(f"/api/tasks/{tid}", headers=auth_headers).status_code == 204
        assert client.patch(f"/api/tasks/{tid}", headers=auth_headers, json={"done": True}).status_code == 404

    def test_link_prospect_ownership(self, client, auth_headers, project_id, db_session):
        from app.models.models import Prospect
        p = Prospect(project_id=project_id, name="A사", email="a@corp.com", status="approved")
        db_session.add(p)
        db_session.commit()
        r = client.post("/api/tasks/", headers=auth_headers,
                        json={"title": "A사 미팅", "prospect_id": p.id})
        assert r.status_code == 201
        assert r.json()["prospect_name"] == "A사"

    def test_link_foreign_prospect_rejected(self, client, auth_headers):
        # 존재하지 않는 prospect_id
        r = client.post("/api/tasks/", headers=auth_headers,
                        json={"title": "x", "prospect_id": 999999})
        assert r.status_code == 404

    def test_cross_user_isolation(self, client, auth_headers, db_session):
        tid = client.post("/api/tasks/", headers=auth_headers, json={"title": "내 할일"}).json()["id"]
        # 다른 유저
        other = client.post("/api/auth/signup", json={
            "email": "other2@x.com", "password": "testpass1234", "name": "o", "accept_terms": True,
        }).json()["token"]
        oh = {"Authorization": f"Bearer {other}"}
        assert client.patch(f"/api/tasks/{tid}", headers=oh, json={"done": True}).status_code == 404
        assert all(t["id"] != tid for t in client.get("/api/tasks/", headers=oh).json())


class TestTaskReminders:
    def test_due_reminder_marks_sent(self, client, auth_headers, db_session, monkeypatch):
        from app.models.models import TaskItem, User
        import app.services.scheduler as sched

        user = db_session.query(User).first()
        soon = (datetime.now(timezone.utc) + timedelta(hours=10)).replace(tzinfo=None)
        t = TaskItem(user_id=user.id, title="마감 임박", due_at=soon)
        db_session.add(t)
        db_session.commit()

        sent = []
        # 시스템 메일 경로 모킹
        monkeypatch.setattr("app.services.sender.email.send_system_email",
                            lambda to, subj, html: sent.append(subj) or True)
        # SessionLocal이 테스트 세션을 쓰도록
        monkeypatch.setattr(sched, "SessionLocal", lambda: db_session)
        # db.close를 무력화 (테스트 세션 유지)
        monkeypatch.setattr(db_session, "close", lambda: None)

        sched.process_task_reminders()
        db_session.refresh(t)
        assert t.reminder_sent_at is not None
