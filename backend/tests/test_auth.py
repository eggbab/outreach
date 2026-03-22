class TestSignup:
    def test_signup_success(self, client):
        response = client.post(
            "/api/auth/signup",
            json={
                "email": "new@example.com",
                "password": "password123",
                "name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "new@example.com"

    def test_signup_duplicate_email(self, client):
        payload = {
            "email": "dup@example.com",
            "password": "password123",
            "name": "First User",
        }
        resp1 = client.post("/api/auth/signup", json=payload)
        assert resp1.status_code == 201

        resp2 = client.post("/api/auth/signup", json=payload)
        assert resp2.status_code == 409
        assert "already registered" in resp2.json()["detail"].lower()


class TestLogin:
    def test_login_success(self, client):
        # First sign up
        client.post(
            "/api/auth/signup",
            json={
                "email": "login@example.com",
                "password": "password123",
                "name": "Login User",
            },
        )
        # Then login
        response = client.post(
            "/api/auth/login",
            json={"email": "login@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "login@example.com"

    def test_login_wrong_password(self, client):
        client.post(
            "/api/auth/signup",
            json={
                "email": "wrong@example.com",
                "password": "correctpassword",
                "name": "Wrong User",
            },
        )
        response = client.post(
            "/api/auth/login",
            json={"email": "wrong@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()


class TestPasswordValidation:
    def test_signup_short_password(self, client):
        response = client.post(
            "/api/auth/signup",
            json={"email": "short@example.com", "password": "1234567", "name": "Short"},
        )
        assert response.status_code == 400

    def test_signup_minimum_password(self, client):
        response = client.post(
            "/api/auth/signup",
            json={"email": "min@example.com", "password": "12345678", "name": "Min"},
        )
        assert response.status_code == 201


class TestSubscription:
    def test_get_usage(self, client, auth_headers):
        response = client.get("/api/subscription/usage", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "limits" in data
        assert "credits" in data
        assert data["emails_sent"] == 0

    def test_credit_packages(self, client):
        response = client.get("/api/subscription/credit-packages")
        assert response.status_code == 200
        assert len(response.json()) == 3


class TestTracking:
    def test_click_rejects_javascript_url(self, client):
        response = client.get("/api/t/click/fake-id?url=javascript:alert(1)", follow_redirects=False)
        assert response.status_code == 400

    def test_click_allows_https_url(self, client):
        response = client.get("/api/t/click/fake-id?url=https://example.com", follow_redirects=False)
        assert response.status_code == 302


class TestGetMe:
    def test_get_me(self, client, auth_headers):
        response = client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"
        assert data["plan"] == "pro"  # 14-day trial
        assert "id" in data
        assert "created_at" in data
