"""인스타 확장 수집 — 큐/결과/저장 계약."""
from app.models.models import InstaCollectJob, Prospect, User


def _headers(client):
    client.post("/api/auth/signup", json={
        "email": "ic@corp.com", "password": "pw12345678",
        "name": "IC", "accept_terms": True})
    tok = client.post("/api/auth/login", json={
        "email": "ic@corp.com", "password": "pw12345678"}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


def _project(client, headers):
    return client.post("/api/projects/", json={"name": "인스타", "description": ""},
                       headers=headers).json()["id"]


class TestInstaCollect:
    def test_enqueue_and_status(self, client, db_session):
        h = _headers(client); pid = _project(client, h)
        r = client.post(f"/api/projects/{pid}/dm/insta-collect",
                        json={"keyword": "#강남카페", "target_count": 15}, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["keyword"] == "강남카페"   # # 제거·정규화

        s = client.get(f"/api/projects/{pid}/dm/insta-collect/status", headers=h).json()
        assert s["status"] == "pending" and s["target"] == 15

    def test_double_enqueue_blocked(self, client, db_session):
        h = _headers(client); pid = _project(client, h)
        client.post(f"/api/projects/{pid}/dm/insta-collect",
                    json={"keyword": "카페"}, headers=h)
        r = client.post(f"/api/projects/{pid}/dm/insta-collect",
                        json={"keyword": "카페"}, headers=h)
        assert r.status_code == 400

    def test_extension_queue_marks_running(self, client, db_session):
        h = _headers(client); pid = _project(client, h)
        client.post(f"/api/projects/{pid}/dm/insta-collect",
                    json={"keyword": "카페"}, headers=h)
        q = client.get(f"/api/chrome/insta-collect-queue?project_id={pid}", headers=h).json()
        assert q["job"]["keyword"] == "카페"
        # 폴링하면 running 으로 전환
        s = client.get(f"/api/projects/{pid}/dm/insta-collect/status", headers=h).json()
        assert s["status"] == "running"

    def test_result_saves_prospects(self, client, db_session):
        h = _headers(client); pid = _project(client, h)
        jid = client.post(f"/api/projects/{pid}/dm/insta-collect",
                          json={"keyword": "카페"}, headers=h).json()["job_id"]
        u = db_session.query(User).filter(User.email == "ic@corp.com").first()
        u.credits = 100; db_session.commit()

        r = client.post("/api/chrome/insta-collect-result", json={
            "job_id": jid, "status": "completed",
            "prospects": [
                {"name": "강남카페", "instagram": "@GangnamCafe",
                 "email": "hi@cafe.kr", "bio": "서울 강남 브런치"},
                {"name": "빈핸들", "instagram": "  "},   # 무효 핸들 → 스킵
            ],
        }, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["saved"] == 1

        p = db_session.query(Prospect).filter(Prospect.project_id == pid).first()
        assert p.instagram == "gangnamcafe"   # 정규화됨
        assert p.email == "hi@cafe.kr"
        assert p.source == "instagram"

        job = db_session.query(InstaCollectJob).filter(InstaCollectJob.id == jid).first()
        assert job.status == "completed" and job.found == 1

    def test_result_rejects_foreign_job(self, client, db_session):
        h = _headers(client); pid = _project(client, h)
        jid = client.post(f"/api/projects/{pid}/dm/insta-collect",
                          json={"keyword": "카페"}, headers=h).json()["job_id"]
        # 다른 사용자
        client.post("/api/auth/signup", json={
            "email": "other@corp.com", "password": "pw12345678",
            "name": "O", "accept_terms": True})
        tok2 = client.post("/api/auth/login", json={
            "email": "other@corp.com", "password": "pw12345678"}).json()["token"]
        r = client.post("/api/chrome/insta-collect-result",
                        json={"job_id": jid, "status": "completed", "prospects": []},
                        headers={"Authorization": f"Bearer {tok2}"})
        assert r.status_code == 404
