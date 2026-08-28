"""서비스 키에 담긴 크레딧이 실제로 지급되는지.

크몽 등 외부에서 결제받고 키만 전달하는 방식이라, 키 등록 = 충전이어야 한다.
예전엔 키를 등록해도 plan만 'pro'로 바뀌고 잔액이 0이라 아무것도 못 했다.
"""
import pytest

from app.models.models import ServiceKey, User


@pytest.fixture
def admin_headers(client, db_session, auth_headers):
    u = db_session.query(User).first()
    u.is_admin = True
    db_session.commit()
    return auth_headers


def _make_key(client, headers, credits, memo="크몽 김철수"):
    r = client.post("/api/admin/service-keys", json={"memo": memo, "credits": credits},
                    headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


class TestServiceKeyCredits:
    def test_key_carries_credit_amount(self, client, admin_headers):
        body = _make_key(client, admin_headers, 30000)
        assert body["credits"] == 30000
        assert body["key"].startswith("sk_")
        assert body["memo"] == "크몽 김철수"

    def test_listed_keys_show_credits(self, client, admin_headers):
        _make_key(client, admin_headers, 10000)
        r = client.get("/api/admin/service-keys", headers=admin_headers)
        assert r.status_code == 200
        assert any(k["credits"] == 10000 for k in r.json())

    def test_negative_credits_rejected(self, client, admin_headers):
        r = client.post("/api/admin/service-keys", json={"memo": "x", "credits": -5},
                        headers=admin_headers)
        assert r.status_code == 400

    def test_activating_key_grants_credits(self, client, admin_headers, db_session):
        """핵심: 키를 등록하면 잔액이 그만큼 늘어야 한다."""
        key = _make_key(client, admin_headers, 30000)["key"]

        # 키를 받을 고객 계정
        client.post("/api/auth/signup", json={
            "email": "buyer@corp.com", "password": "pw12345678",
            "name": "구매자", "accept_terms": True,
        })
        login = client.post("/api/auth/login", json={
            "email": "buyer@corp.com", "password": "pw12345678"}).json()
        buyer_headers = {"Authorization": f"Bearer {login['token']}"}

        before = db_session.query(User).filter(User.email == "buyer@corp.com").first().credits

        r = client.post("/api/auth/activate-key", json={"service_key": key},
                        headers=buyer_headers)
        assert r.status_code == 200, r.text
        assert r.json()["credits_granted"] == 30000

        db_session.expire_all()
        after = db_session.query(User).filter(User.email == "buyer@corp.com").first().credits
        assert after == before + 30000, "키에 담긴 크레딧이 지급되지 않았습니다"

    def test_zero_credit_key_still_activates(self, client, admin_headers):
        """수량 0짜리 키(등급만 부여)도 오류 없이 동작해야 한다."""
        key = _make_key(client, admin_headers, 0, memo="등급만")["key"]
        client.post("/api/auth/signup", json={
            "email": "zero@corp.com", "password": "pw12345678",
            "name": "제로", "accept_terms": True,
        })
        login = client.post("/api/auth/login", json={
            "email": "zero@corp.com", "password": "pw12345678"}).json()
        r = client.post("/api/auth/activate-key", json={"service_key": key},
                        headers={"Authorization": f"Bearer {login['token']}"})
        assert r.status_code == 200
        assert r.json()["credits_granted"] == 0

    def test_key_cannot_be_reused(self, client, admin_headers):
        """한 번 쓴 키로 두 번 충전되면 안 된다."""
        key = _make_key(client, admin_headers, 5000)["key"]
        for i, email in enumerate(("a@corp.com", "b@corp.com")):
            client.post("/api/auth/signup", json={
                "email": email, "password": "pw12345678",
                "name": f"u{i}", "accept_terms": True,
            })
            login = client.post("/api/auth/login", json={
                "email": email, "password": "pw12345678"}).json()
            r = client.post("/api/auth/activate-key", json={"service_key": key},
                            headers={"Authorization": f"Bearer {login['token']}"})
            if i == 0:
                assert r.status_code == 200
            else:
                assert r.status_code == 400  # 이미 사용된 키

    def test_signup_with_key_also_grants(self, client, admin_headers, db_session):
        """가입할 때 키를 넣은 경우에도 충전돼야 한다."""
        key = _make_key(client, admin_headers, 7000, memo="가입동시")["key"]
        r = client.post("/api/auth/signup", json={
            "email": "withkey@corp.com", "password": "pw12345678",
            "name": "키동봉", "accept_terms": True, "service_key": key,
        })
        assert r.status_code == 201, r.text
        db_session.expire_all()
        u = db_session.query(User).filter(User.email == "withkey@corp.com").first()
        from app.core.plans import FREE_SIGNUP_CREDITS
        assert u.credits == FREE_SIGNUP_CREDITS + 7000

    def test_non_admin_cannot_issue_keys(self, client, auth_headers, db_session):
        u = db_session.query(User).first()
        u.is_admin = False
        db_session.commit()
        r = client.post("/api/admin/service-keys", json={"memo": "x", "credits": 999},
                        headers=auth_headers)
        assert r.status_code in (401, 403)
