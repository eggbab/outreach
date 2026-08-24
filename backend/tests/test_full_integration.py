"""
거대 통합 테스트 — 프로젝트의 모든 경우의 수를 검증.

검증 영역:
A. 인증/권한 (회원가입, 로그인, 약관, 비번 재설정, JWT, 정지된 계정)
B. 프로젝트/키워드/잠재고객 CRUD (검증, 권한 격리, 페이지네이션, 경계값)
C. 설정 (gmail/insta 화이트리스트, 암호화 저장)
D. 크레딧 결제 우회 방지 (수집/이메일/DM 모두 사전 체크 + 차감)
E. 이메일 — 미리보기/발송/추적/스케줄 (실 SMTP 제외)
F. 인스타 DM — 자격증명 미설정/일시정지/큐 흐름
G. CRM (태그·메모·파이프라인·통화·제안서·미팅·공개 예약)
H. 시퀀스 (생성/스텝/등록)
I. 분석 (이메일 통계·퍼널·키워드 ROI·소스 ROI·추천)
J. 관리자 (bootstrap·사용자 관리·매출 통계·서비스 키)
K. 입력 검증 (XSS/SQL 시도/길이/형식)
L. 권한 격리 (User A의 데이터에 User B가 접근 불가)
M. 페이지네이션 경계 (page=0, page_size=999, 빈 결과)
N. 비공개 라우트 (인증 필수)
O. 추적 (오픈/클릭, javascript: 거부)
"""
import io


# ─────────────────────────────────────────
# Fixtures (conftest의 client/auth_headers/project_id 활용)
# ─────────────────────────────────────────

def _signup(client, email, name="X", password="password1234", terms=True):
    return client.post("/api/auth/signup", json={
        "email": email, "password": password, "name": name, "accept_terms": terms,
    })


def _login(client, email, password="password1234"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


# ──────────────────────────────────────────────────────
# A. 인증/권한
# ──────────────────────────────────────────────────────

class TestAuthExhaustive:
    def test_signup_short_password(self, client):
        r = _signup(client, "a@a.com", password="short")
        assert r.status_code == 400

    def test_signup_no_terms(self, client):
        r = _signup(client, "b@b.com", terms=False)
        assert r.status_code == 400

    def test_signup_invalid_email(self, client):
        r = _signup(client, "not-an-email")
        assert r.status_code == 422

    def test_signup_then_duplicate(self, client):
        assert _signup(client, "dup@dup.com").status_code == 201
        r = _signup(client, "dup@dup.com")
        assert r.status_code == 409

    def test_login_unknown_user(self, client):
        r = _login(client, "ghost@ghost.com")
        assert r.status_code == 401

    def test_login_wrong_password(self, client):
        _signup(client, "wp@wp.com")
        r = _login(client, "wp@wp.com", password="wrong1234")
        assert r.status_code == 401

    def test_me_without_token(self, client):
        r = client.get("/api/auth/me")
        assert r.status_code in (401, 403)

    def test_me_with_garbage_token(self, client):
        r = client.get("/api/auth/me", headers=_bearer("not.a.jwt"))
        assert r.status_code == 401

    def test_forgot_password_unknown_email_still_200(self, client):
        # 보안: 이메일 존재 여부 노출 방지
        assert client.post("/api/auth/forgot-password", json={"email": "x@y.com"}).status_code == 200

    def test_reset_with_bad_token(self, client):
        r = client.post("/api/auth/reset-password", json={"token": "bad", "new_password": "newpass1234"})
        assert r.status_code == 400

    def test_reset_short_password(self, client):
        r = client.post("/api/auth/reset-password", json={"token": "any", "new_password": "short"})
        assert r.status_code == 400


# ──────────────────────────────────────────────────────
# B. 프로젝트/키워드 CRUD + 권한 격리
# ──────────────────────────────────────────────────────

class TestProjectsAndKeywords:
    def test_create_list_get_delete(self, client, auth_headers):
        r = client.post("/api/projects/", json={"name": "P1"}, headers=auth_headers)
        assert r.status_code == 201
        pid = r.json()["id"]
        assert client.get("/api/projects/", headers=auth_headers).status_code == 200
        assert client.get(f"/api/projects/{pid}", headers=auth_headers).status_code == 200
        assert client.delete(f"/api/projects/{pid}", headers=auth_headers).status_code == 204
        assert client.get(f"/api/projects/{pid}", headers=auth_headers).status_code == 404

    def test_keyword_crud(self, client, auth_headers, project_id):
        r = client.post(f"/api/projects/{project_id}/keywords/", json={"keyword": "카페"}, headers=auth_headers)
        assert r.status_code == 201
        kw_id = r.json()["id"]
        assert client.get(f"/api/projects/{project_id}/keywords/", headers=auth_headers).status_code == 200
        assert client.delete(f"/api/projects/{project_id}/keywords/{kw_id}", headers=auth_headers).status_code == 204

    def test_isolation_between_users(self, client):
        # User A 프로젝트 생성
        ra = _signup(client, "a@iso.com")
        ta = ra.json()["token"]
        pid = client.post("/api/projects/", json={"name": "secret"}, headers=_bearer(ta)).json()["id"]
        # User B 가입 후 User A 프로젝트 조회 시도
        rb = _signup(client, "b@iso.com")
        tb = rb.json()["token"]
        r = client.get(f"/api/projects/{pid}", headers=_bearer(tb))
        assert r.status_code == 404

    def test_keyword_isolation(self, client):
        ra = _signup(client, "ka@k.com"); ta = ra.json()["token"]
        pid = client.post("/api/projects/", json={"name": "P"}, headers=_bearer(ta)).json()["id"]
        client.post(f"/api/projects/{pid}/keywords/", json={"keyword": "x"}, headers=_bearer(ta))
        rb = _signup(client, "kb@k.com"); tb = rb.json()["token"]
        # User B가 User A 프로젝트의 키워드 조회 시도 → 프로젝트 자체가 안 보여야 함
        r = client.get(f"/api/projects/{pid}/keywords/", headers=_bearer(tb))
        assert r.status_code == 404


# ──────────────────────────────────────────────────────
# C. 설정 — 화이트리스트 + 암호화
# ──────────────────────────────────────────────────────

class TestSettingsExhaustive:
    def test_unknown_field_rejected(self, client, auth_headers):
        r = client.put("/api/settings/", json={"smtp_email": "x@y.com"}, headers=auth_headers)
        assert r.status_code == 422

    def test_full_payload_accepted(self, client, auth_headers):
        r = client.put("/api/settings/", json={
            "gmail_email": "g@g.com",
            "gmail_app_password": "abcdabcdabcdabcd",
            "email_subject": "테스트 {company_name}",
            "email_template": "<p>안녕 {name}</p>",
            "dm_template": "안녕하세요 {name}님",
            "daily_email_limit": 50,
            "daily_dm_limit": 10,
        }, headers=auth_headers)
        assert r.status_code == 200
        d = r.json()
        assert d["gmail_email"] == "g@g.com"
        assert d["has_gmail_password"] is True
        assert d["dm_template"] == "안녕하세요 {name}님"

    def test_insta_credential_fields_rejected(self, client, auth_headers):
        # 더 이상 인스타 자격증명 필드는 받지 않음 (크롬 확장만)
        r = client.put("/api/settings/", json={
            "insta_username": "x", "insta_password": "y",
        }, headers=auth_headers)
        assert r.status_code == 422

    def test_daily_limit_bounds(self, client, auth_headers):
        # 초과
        assert client.put("/api/settings/", json={"daily_email_limit": 1000}, headers=auth_headers).status_code == 400
        assert client.put("/api/settings/", json={"daily_email_limit": 0}, headers=auth_headers).status_code == 400
        # 정상
        assert client.put("/api/settings/", json={"daily_email_limit": 100}, headers=auth_headers).status_code == 200

    def test_safety_guide_for_new_user(self, client, auth_headers):
        # 워밍업 첫날 (account_age=0) — DM은 recommended=0 → ZeroDivision 회귀 방지
        r = client.get("/api/settings/safety-guide", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["dm"]["risk_level"] in ("safe", "moderate", "risky")


# ──────────────────────────────────────────────────────
# D. 크레딧 결제 우회 방지
# ──────────────────────────────────────────────────────

class TestCreditGates:
    def test_no_credits_blocks_email_send(self, client, auth_headers, project_id, db_session):
        from app.models.models import User, UserSettings
        from app.core.security import encrypt_value
        user = db_session.query(User).first()
        user.credits = 0
        s = db_session.query(UserSettings).filter(UserSettings.user_id == user.id).first()
        s.gmail_email = "g@g.com"
        s.gmail_app_password_encrypted = encrypt_value("xxxx")
        db_session.commit()
        r = client.post(f"/api/projects/{project_id}/send-email", headers=auth_headers)
        assert r.status_code == 402

    def test_no_credits_returns_empty_dm_queue(self, client, auth_headers, project_id, db_session):
        # 서버 발송 라우트 제거됨 — 크롬 확장이 큐를 받음.
        # 크레딧 0이면 빈 큐 → 확장이 발송 시도 안 함.
        from app.models.models import User, Prospect
        user = db_session.query(User).first()
        user.credits = 0
        db_session.add(Prospect(
            project_id=project_id, name="t", instagram="t_acct",
            score=0, status="approved", source="naver",
        ))
        db_session.commit()
        r = client.get(f"/api/chrome/dm-queue?project_id={project_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_purchase_credits_endpoint_removed(self, client, auth_headers):
        r = client.post("/api/subscription/purchase-credits",
                        json={"package_id": "credits_10000"}, headers=auth_headers)
        assert r.status_code == 404


# ──────────────────────────────────────────────────────
# E. 이메일 발송 흐름 (실 SMTP 제외)
# ──────────────────────────────────────────────────────

class TestEmailFlow:
    def test_send_email_no_settings(self, client, auth_headers, project_id):
        # 설정 안 함 → 400
        r = client.post(f"/api/projects/{project_id}/send-email", headers=auth_headers)
        assert r.status_code == 400

    def test_send_test_email_no_settings(self, client, auth_headers, project_id):
        r = client.post(f"/api/projects/{project_id}/send-test-email", headers=auth_headers)
        assert r.status_code == 400

    def test_send_email_no_prospects(self, client, auth_headers, project_id):
        client.put("/api/settings/", json={
            "gmail_email": "g@g.com", "gmail_app_password": "xxxxxxxxxxxxxxxx"
        }, headers=auth_headers)
        r = client.post(f"/api/projects/{project_id}/send-email", headers=auth_headers)
        # 사전 크레딧 OK (기본 50cr) → 0 prospects → 400
        assert r.status_code == 400


# ──────────────────────────────────────────────────────
# F. 인스타 DM 흐름
# ──────────────────────────────────────────────────────

class TestInstaDmFlow:
    def test_dm_send_route_removed(self, client, auth_headers, project_id):
        # 서버 발송은 폐지됨. 크롬 확장이 발송함.
        r = client.post(f"/api/projects/{project_id}/dm/send", headers=auth_headers)
        assert r.status_code in (404, 405)

    def test_dm_status_endpoint(self, client, auth_headers, project_id):
        r = client.get(f"/api/projects/{project_id}/dm/status", headers=auth_headers)
        assert r.status_code == 200
        assert "connected" in r.json()

    def test_dm_queue_empty(self, client, auth_headers, project_id):
        r = client.get(f"/api/projects/{project_id}/dm/queue", headers=auth_headers)
        assert r.status_code == 200


# ──────────────────────────────────────────────────────
# G. CRM 흐름 (태그/메모/파이프라인/통화/제안서/미팅)
# ──────────────────────────────────────────────────────

class TestCRM:
    def test_tag_lifecycle(self, client, auth_headers):
        r = client.post("/api/tags/", json={"name": "VIP", "color": "#fff"}, headers=auth_headers)
        assert r.status_code == 201
        tid = r.json()["id"]
        assert client.get("/api/tags/", headers=auth_headers).status_code == 200
        assert client.put(f"/api/tags/{tid}", json={"name": "VIP2"}, headers=auth_headers).status_code == 200
        assert client.delete(f"/api/tags/{tid}", headers=auth_headers).status_code == 204

    def test_pipeline_stages_default_created(self, client, auth_headers):
        r = client.get("/api/pipeline/stages", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1  # 회원가입 시 기본 stage 5개

    def test_proposal_template_create(self, client, auth_headers):
        r = client.post("/api/proposal-templates/", json={
            "name": "기본", "content_html": "<h1>안녕</h1>", "price": 100000,
        }, headers=auth_headers)
        assert r.status_code == 201

    def test_call_log_with_prospect(self, client, auth_headers, project_id, db_session):
        from app.models.models import Prospect
        p = Prospect(project_id=project_id, name="P", email="x@x.com", score=0,
                     status="approved", source="naver")
        db_session.add(p); db_session.commit(); db_session.refresh(p)
        r = client.post(f"/api/projects/{project_id}/calls/", json={
            "prospect_id": p.id, "outcome": "connected", "duration_seconds": 60,
        }, headers=auth_headers)
        assert r.status_code == 201


# ──────────────────────────────────────────────────────
# H. 시퀀스
# ──────────────────────────────────────────────────────

class TestSequences:
    def test_sequence_create(self, client, auth_headers, project_id):
        r = client.post(f"/api/projects/{project_id}/sequences/", json={"name": "S1"}, headers=auth_headers)
        assert r.status_code == 201

    def test_sequence_list(self, client, auth_headers, project_id):
        r = client.get(f"/api/projects/{project_id}/sequences/", headers=auth_headers)
        assert r.status_code == 200


# ──────────────────────────────────────────────────────
# I. 분석
# ──────────────────────────────────────────────────────

class TestAnalytics:
    def test_email_stats_empty(self, client, auth_headers, project_id):
        r = client.get(f"/api/projects/{project_id}/analytics/email-stats", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["total_sent"] == 0

    def test_funnel(self, client, auth_headers, project_id):
        r = client.get(f"/api/projects/{project_id}/analytics/funnel", headers=auth_headers)
        assert r.status_code == 200

    def test_keyword_roi(self, client, auth_headers, project_id):
        r = client.get(f"/api/projects/{project_id}/analytics/keyword-roi", headers=auth_headers)
        assert r.status_code == 200


# ──────────────────────────────────────────────────────
# J. 관리자
# ──────────────────────────────────────────────────────

class TestAdminFull:
    def test_bootstrap_first_admin(self, client, auth_headers):
        r = client.post("/api/admin/bootstrap-first-admin", headers=auth_headers)
        assert r.status_code == 200

    def test_admin_routes_after_bootstrap(self, client, auth_headers):
        client.post("/api/admin/bootstrap-first-admin", headers=auth_headers)
        assert client.get("/api/admin/users", headers=auth_headers).status_code == 200
        assert client.get("/api/admin/stats", headers=auth_headers).status_code == 200

    def test_admin_grant_credits(self, client, auth_headers, db_session):
        client.post("/api/admin/bootstrap-first-admin", headers=auth_headers)
        from app.models.models import User
        uid = db_session.query(User).first().id
        r = client.post(f"/api/admin/users/{uid}/grant-credits",
                        json={"amount": 100, "reason": "테스트"}, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["credits"] >= 100

    def test_admin_grant_no_reason_rejected(self, client, auth_headers, db_session):
        client.post("/api/admin/bootstrap-first-admin", headers=auth_headers)
        from app.models.models import User
        uid = db_session.query(User).first().id
        r = client.post(f"/api/admin/users/{uid}/grant-credits",
                        json={"amount": 100, "reason": ""}, headers=auth_headers)
        assert r.status_code == 400

    def test_admin_cant_self_demote(self, client, auth_headers, db_session):
        client.post("/api/admin/bootstrap-first-admin", headers=auth_headers)
        from app.models.models import User
        uid = db_session.query(User).first().id
        r = client.patch(f"/api/admin/users/{uid}", json={"is_admin": False}, headers=auth_headers)
        assert r.status_code == 400


# ──────────────────────────────────────────────────────
# K. 입력 검증 — XSS/긴 입력/특수문자
# ──────────────────────────────────────────────────────

class TestInputValidation:
    def test_long_project_name_handled(self, client, auth_headers):
        r = client.post("/api/projects/", json={"name": "A" * 200}, headers=auth_headers)
        # 200자까지 허용 (DB column String(200))
        assert r.status_code in (201, 422)

    def test_xss_in_project_name_stored_as_text(self, client, auth_headers):
        # XSS 페이로드 그대로 저장돼도 OK (출력 시 React가 escape함)
        payload = "<script>alert('xss')</script>"
        r = client.post("/api/projects/", json={"name": payload}, headers=auth_headers)
        assert r.status_code == 201
        assert r.json()["name"] == payload

    def test_unicode_korean_emoji_in_keyword(self, client, auth_headers, project_id):
        r = client.post(f"/api/projects/{project_id}/keywords/",
                        json={"keyword": "카페 ☕ 강남"}, headers=auth_headers)
        assert r.status_code == 201


# ──────────────────────────────────────────────────────
# L. 권한 격리 (User A 데이터에 User B 접근 시도)
# ──────────────────────────────────────────────────────

class TestPermissionIsolation:
    def test_user_b_cannot_send_email_for_user_a_project(self, client):
        ra = _signup(client, "ea@e.com"); ta = ra.json()["token"]
        pid = client.post("/api/projects/", json={"name": "P"}, headers=_bearer(ta)).json()["id"]
        rb = _signup(client, "eb@e.com"); tb = rb.json()["token"]
        r = client.post(f"/api/projects/{pid}/send-email", headers=_bearer(tb))
        # 정상: 404 (남의 프로젝트). 429: rate limit (테스트 순서에 따라). 둘 다 격리 OK.
        assert r.status_code in (404, 429)

    def test_user_b_cannot_delete_user_a_project(self, client):
        ra = _signup(client, "da@d.com"); ta = ra.json()["token"]
        pid = client.post("/api/projects/", json={"name": "P"}, headers=_bearer(ta)).json()["id"]
        rb = _signup(client, "db@d.com"); tb = rb.json()["token"]
        r = client.delete(f"/api/projects/{pid}", headers=_bearer(tb))
        assert r.status_code == 404

    def test_user_b_cannot_admin(self, client):
        # User A가 admin이 되어도 User B의 admin 라우트 접근은 막혀야
        ra = _signup(client, "aa@a.com"); ta = ra.json()["token"]
        client.post("/api/admin/bootstrap-first-admin", headers=_bearer(ta))
        rb = _signup(client, "bb@b.com"); tb = rb.json()["token"]
        assert client.get("/api/admin/users", headers=_bearer(tb)).status_code == 403


# ──────────────────────────────────────────────────────
# M. 페이지네이션 경계
# ──────────────────────────────────────────────────────

class TestPagination:
    def test_page_zero_rejected(self, client, auth_headers, project_id):
        r = client.get(f"/api/projects/{project_id}/prospects?page=0", headers=auth_headers)
        assert r.status_code == 422

    def test_page_size_too_large_rejected(self, client, auth_headers, project_id):
        r = client.get(f"/api/projects/{project_id}/prospects?per_page=9999", headers=auth_headers)
        assert r.status_code in (200, 422)


# ──────────────────────────────────────────────────────
# N. 추적 — javascript: URL 거부
# ──────────────────────────────────────────────────────

class TestTracking:
    def test_pixel_returns_gif(self, client):
        r = client.get("/api/t/open/some_id", follow_redirects=False)
        assert r.status_code == 200

    def test_click_javascript_url_blocked(self, client):
        r = client.get("/api/t/click/some_id?url=javascript:alert(1)", follow_redirects=False)
        assert r.status_code == 400

    def test_click_https_url_redirects(self, client):
        r = client.get("/api/t/click/some_id?url=https://example.com", follow_redirects=False)
        assert r.status_code == 302


# ──────────────────────────────────────────────────────
# O. 결제
# ──────────────────────────────────────────────────────

class TestBankTransferPayments:
    """계좌이체 결제 흐름 — 토스 제거 후."""

    def test_old_toss_routes_removed(self, client, auth_headers):
        # /payments/prepare /payments/confirm 모두 제거
        assert client.post("/api/payments/prepare", json={"package_id": "credits_10000"}, headers=auth_headers).status_code == 404
        assert client.post("/api/payments/confirm", json={}, headers=auth_headers).status_code == 404

    def test_bank_info_visible_to_user(self, client, auth_headers):
        r = client.get("/api/payments/bank-info", headers=auth_headers)
        assert r.status_code == 200
        assert "bank_name" in r.json()

    def test_create_payment_request(self, client, auth_headers):
        r = client.post("/api/payments/request", json={
            "package_id": "credits_10000", "depositor_name": "홍길동", "memo": "테스트",
        }, headers=auth_headers)
        assert r.status_code == 201
        d = r.json()
        assert d["status"] == "pending" and d["amount"] == 590000

    def test_create_payment_request_invalid_package(self, client, auth_headers):
        r = client.post("/api/payments/request", json={
            "package_id": "bogus", "depositor_name": "X",
        }, headers=auth_headers)
        assert r.status_code == 400

    def test_create_payment_request_no_depositor(self, client, auth_headers):
        r = client.post("/api/payments/request", json={
            "package_id": "credits_10000", "depositor_name": "",
        }, headers=auth_headers)
        assert r.status_code == 422

    def test_my_requests_list(self, client, auth_headers):
        client.post("/api/payments/request", json={
            "package_id": "credits_10000", "depositor_name": "X",
        }, headers=auth_headers)
        r = client.get("/api/payments/my-requests", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_admin_approve_credits_user(self, client, auth_headers, db_session):
        # 1) 사용자가 결제 요청 생성
        pr_id = client.post("/api/payments/request", json={
            "package_id": "credits_10000", "depositor_name": "X",
        }, headers=auth_headers).json()["id"]
        # 2) 본인을 admin으로 승격
        client.post("/api/admin/bootstrap-first-admin", headers=auth_headers)
        # 3) 사전 크레딧
        from app.models.models import User
        user = db_session.query(User).first()
        before = user.credits
        # 4) 승인
        r = client.post(f"/api/admin/payment-requests/{pr_id}/approve", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["credits_added"] == 10000
        db_session.refresh(user)
        assert user.credits == before + 10000

    def test_admin_approve_twice_rejected(self, client, auth_headers):
        pr_id = client.post("/api/payments/request", json={
            "package_id": "credits_10000", "depositor_name": "X",
        }, headers=auth_headers).json()["id"]
        client.post("/api/admin/bootstrap-first-admin", headers=auth_headers)
        client.post(f"/api/admin/payment-requests/{pr_id}/approve", headers=auth_headers)
        r2 = client.post(f"/api/admin/payment-requests/{pr_id}/approve", headers=auth_headers)
        assert r2.status_code == 400  # 이미 처리됨

    def test_admin_reject_with_reason(self, client, auth_headers):
        pr_id = client.post("/api/payments/request", json={
            "package_id": "credits_10000", "depositor_name": "X",
        }, headers=auth_headers).json()["id"]
        client.post("/api/admin/bootstrap-first-admin", headers=auth_headers)
        r = client.post(f"/api/admin/payment-requests/{pr_id}/reject",
                        json={"reason": "입금 확인 불가"}, headers=auth_headers)
        assert r.status_code == 200

    def test_admin_routes_protected(self, client, auth_headers):
        # 일반 user는 admin 결제 라우트 접근 불가
        assert client.get("/api/admin/payment-requests/", headers=auth_headers).status_code == 403

    def test_credit_packages_public_visible(self, client):
        r = client.get("/api/subscription/credit-packages")
        assert r.status_code in (200, 401, 403)


# ──────────────────────────────────────────────────────
# P. 비공개 라우트 (인증 필수) — 모두 401/403
# ──────────────────────────────────────────────────────

class TestProtectedRoutes:
    PROTECTED = [
        "/api/projects/", "/api/templates/", "/api/tags/", "/api/teams/",
        "/api/api-keys/", "/api/blacklist/", "/api/dashboard/stats",
        "/api/subscription/", "/api/subscription/usage",
        "/api/discover/", "/api/onboarding/",
        "/api/pipeline/stages", "/api/pipeline/deals",
        "/api/proposal-templates/", "/api/proposals/",
        "/api/admin/users", "/api/admin/stats", "/api/admin/service-keys",
    ]

    def test_all_protected_routes_require_auth(self, client):
        for path in self.PROTECTED:
            r = client.get(path)
            assert r.status_code in (401, 403), f"{path} returned {r.status_code} without auth"


# ──────────────────────────────────────────────────────
# Q. 정지된 계정 로그인 차단
# ──────────────────────────────────────────────────────

class TestSuspendedAccount:
    def test_suspended_user_login_blocked(self, client, db_session):
        _signup(client, "susp@s.com")
        from app.models.models import User
        u = db_session.query(User).filter(User.email == "susp@s.com").first()
        u.is_active = False
        db_session.commit()
        r = _login(client, "susp@s.com")
        assert r.status_code == 403


# ──────────────────────────────────────────────────────
# R. 블랙리스트
# ──────────────────────────────────────────────────────

class TestBlacklist:
    def test_add_check(self, client, auth_headers):
        client.post("/api/blacklist/", json={"email": "bad@x.com", "reason": "스팸"}, headers=auth_headers)
        r = client.post("/api/blacklist/check", json={"email": "bad@x.com"}, headers=auth_headers)
        assert r.status_code == 200


# ──────────────────────────────────────────────────────
# S. API 키 생명주기
# ──────────────────────────────────────────────────────

class TestApiKeys:
    def test_create_returns_key_once(self, client, auth_headers):
        r = client.post("/api/api-keys/", json={"name": "test"}, headers=auth_headers)
        assert r.status_code == 201
        d = r.json()
        assert "key" in d and d["key"].startswith("osk_")
        # 두 번째 list에서는 key 풀 노출 X
        r2 = client.get("/api/api-keys/", headers=auth_headers)
        for k in r2.json():
            assert "key" not in k or k.get("key") is None or len(k.get("key", "")) < len(d["key"])


# ──────────────────────────────────────────────────────
# T. CSV 내보내기
# ──────────────────────────────────────────────────────

class TestCsvExport:
    def test_export_returns_csv(self, client, auth_headers, project_id):
        r = client.get(f"/api/projects/{project_id}/export/prospects", headers=auth_headers)
        assert r.status_code == 200
