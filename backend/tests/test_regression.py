"""이번 점검에서 발견·수정한 버그들의 회귀 방지."""


class TestSafetyGuide:
    """plans.py:198 ZeroDivisionError 회귀 방지 — 신규 계정에서 호출되어야 한다."""

    def test_safety_guide_returns_200_for_new_account(self, client, auth_headers):
        r = client.get("/api/settings/safety-guide", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "email" in body and "dm" in body
        # DM은 워밍업 첫날 recommended=0 → risky 분기 안 들어가야 함
        assert "risk_level" in body["dm"]


class TestSettingsExtraForbid:
    """settings.py — 잘못된 필드명이 silent ignore되지 않아야 한다."""

    def test_settings_put_rejects_unknown_field(self, client, auth_headers):
        r = client.put(
            "/api/settings/",
            json={"smtp_email": "x@y.com"},  # 옳은 이름은 gmail_email
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_settings_put_accepts_correct_field(self, client, auth_headers):
        r = client.put(
            "/api/settings/",
            json={"gmail_email": "ok@example.com"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["gmail_email"] == "ok@example.com"


class TestPurchaseCreditsRemoved:
    """결제 검증 우회 취약점 회귀 방지 — 이 라우트가 절대 부활하면 안 된다."""

    def test_purchase_credits_route_removed(self, client, auth_headers):
        r = client.post(
            "/api/subscription/purchase-credits",
            json={"package_id": "credits_10000"},
            headers=auth_headers,
        )
        assert r.status_code == 404


class TestAuthOnAllProtectedRoutes:
    """모든 보호 라우트는 토큰 없으면 401/403."""

    def test_routes_require_auth(self, client):
        protected = [
            "/api/projects/",
            "/api/templates/",
            "/api/tags/",
            "/api/teams/",
            "/api/api-keys/",
            "/api/blacklist/",
            "/api/dashboard/stats",
            "/api/subscription/",
            "/api/subscription/usage",
            "/api/discover/",
            "/api/admin/service-keys",
            "/api/onboarding/",
        ]
        for path in protected:
            r = client.get(path)
            assert r.status_code in (401, 403), f"{path} returned {r.status_code} without auth"


class TestAdminOnlyRoutes:
    """일반 user 토큰으로 admin 라우트 접근 시 403."""

    def test_admin_route_blocks_normal_user(self, client, auth_headers):
        r = client.get("/api/admin/service-keys", headers=auth_headers)
        assert r.status_code == 403


class TestTermsAcceptance:
    """약관 동의 안하면 가입 거부."""

    def test_signup_without_terms_rejected(self, client):
        r = client.post(
            "/api/auth/signup",
            json={
                "email": "noterm@example.com",
                "password": "password123",
                "name": "X",
                # accept_terms 누락 = 기본값 False
            },
        )
        assert r.status_code == 400
        assert "약관" in r.json()["detail"]


class TestPasswordReset:
    """비밀번호 재설정 흐름 — forgot/reset이 정상 동작."""

    def test_forgot_password_always_returns_200(self, client):
        # 존재하지 않는 이메일에도 200 (이메일 존재 여부 노출 방지)
        r = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
        assert r.status_code == 200

    def test_reset_with_invalid_token_400(self, client):
        r = client.post("/api/auth/reset-password", json={"token": "fake", "new_password": "newpassword123"})
        assert r.status_code == 400


class TestAdminBootstrap:
    """관리자가 한 명도 없으면 첫 사용자가 본인을 승격할 수 있다."""

    def test_first_admin_bootstrap(self, client, auth_headers):
        r = client.post("/api/admin/bootstrap-first-admin", headers=auth_headers)
        assert r.status_code == 200
        # 두 번째 호출은 실패해야 함
        r2 = client.post("/api/admin/bootstrap-first-admin", headers=auth_headers)
        assert r2.status_code == 403
