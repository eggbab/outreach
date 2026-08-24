"""신규 수집 채널(카카오 공식 API) + 이메일 MX 검증 테스트."""
import json

import pytest

from app.models.models import GlobalUnsubscribe, Prospect, User
from app.services import email_verify
from app.services.collector import kakao


# ──────────────────────────────────────
# 카카오 로컬 API 수집기
# ──────────────────────────────────────

class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        pass


class _FakeClient:
    def __init__(self, payload, **kwargs):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def get(self, url, headers=None, params=None):
        return _FakeResponse(self._payload)


KAKAO_PAYLOAD = {
    "documents": [
        {
            "place_name": "성수 테스트 카페",
            "phone": "02-1234-5678",
            "category_name": "음식점 > 카페 > 커피전문점",
            "place_url": "http://place.map.kakao.com/123",
            "road_address_name": "서울 성동구 성수동 12",
        },
        {
            "place_name": "전화없는집",
            "phone": "",
            "category_name": "음식점 > 카페",
            "place_url": "http://place.map.kakao.com/456",
            "road_address_name": "서울 성동구 성수동 34",
        },
    ],
    "meta": {"is_end": True},
}


class TestKakaoCollector:
    def test_skips_without_api_key(self, monkeypatch):
        monkeypatch.delenv("KAKAO_REST_API_KEY", raising=False)
        assert kakao.search_kakao("성수동 카페") == []

    def test_collects_with_phone_only(self, monkeypatch):
        monkeypatch.setenv("KAKAO_REST_API_KEY", "test-key")
        monkeypatch.setattr(kakao.httpx, "Client", lambda **kw: _FakeClient(KAKAO_PAYLOAD))
        results = kakao.search_kakao("성수동 카페", max_results=10)
        # 전화번호 없는 업체는 제외
        assert len(results) == 1
        r = results[0]
        assert r["name"] == "성수 테스트 카페"
        assert r["phone"] == "02-1234-5678"
        assert r["source"] == "kakao"
        assert r["category"] == "커피전문점"
        assert r["address"].startswith("서울 성동구")

    def test_respects_max_results(self, monkeypatch):
        monkeypatch.setenv("KAKAO_REST_API_KEY", "test-key")
        many = {
            "documents": [
                {"place_name": f"업체{i}", "phone": f"02-000-{i:04d}", "category_name": "카페"}
                for i in range(15)
            ],
            "meta": {"is_end": True},
        }
        monkeypatch.setattr(kakao.httpx, "Client", lambda **kw: _FakeClient(many))
        assert len(kakao.search_kakao("카페", max_results=3)) == 3


# ──────────────────────────────────────
# 이메일 MX 검증
# ──────────────────────────────────────

class TestEmailVerify:
    def setup_method(self):
        email_verify._domain_cache.clear()

    def test_known_good_domain(self):
        assert email_verify.check_email_domain("someone@gmail.com") is True
        assert email_verify.check_email_domain("someone@naver.com") is True

    def test_invalid_format(self):
        assert email_verify.check_email_domain(None) is None
        assert email_verify.check_email_domain("not-an-email") is None
        assert email_verify.check_email_domain("x@nodot") is False

    def test_nxdomain_is_false_and_cached(self, monkeypatch):
        import dns.resolver

        class FakeResolver:
            timeout = 0
            lifetime = 0
            calls = 0

            def resolve(self, domain, rtype):
                FakeResolver.calls += 1
                raise dns.resolver.NXDOMAIN()

        monkeypatch.setattr(dns.resolver, "Resolver", FakeResolver)
        assert email_verify.check_email_domain("a@no-such-domain-xyz.kr") is False
        # 캐시 적중 — resolver 재호출 없음
        calls_before = FakeResolver.calls
        assert email_verify.check_email_domain("b@no-such-domain-xyz.kr") is False
        assert FakeResolver.calls == calls_before

    def test_mx_found_is_true(self, monkeypatch):
        import dns.resolver

        class FakeResolver:
            timeout = 0
            lifetime = 0

            def resolve(self, domain, rtype):
                return ["mx1"]

        monkeypatch.setattr(dns.resolver, "Resolver", FakeResolver)
        assert email_verify.check_email_domain("a@company-with-mx.co.kr") is True


# ──────────────────────────────────────
# 발송 시 MX 실패 스킵
# ──────────────────────────────────────

class TestSendSkipsInvalidEmail:
    def test_invalid_email_skipped_no_charge(self, client, auth_headers, project_id, db_session, monkeypatch):
        from app.services.sender import email as email_mod

        user = db_session.query(User).first()
        start = user.credits
        good = Prospect(project_id=project_id, name="정상", email="ok@corp.com",
                        email_valid=True, status="approved")
        bad = Prospect(project_id=project_id, name="반송될곳", email="dead@invalid.xyz",
                       email_valid=False, status="approved")
        db_session.add_all([good, bad])
        db_session.commit()

        sent = []
        monkeypatch.setattr(email_mod, "send_email", lambda **kw: sent.append(kw) or True)

        result = email_mod.send_bulk_emails(
            db=db_session, gmail_email="me@gmail.com", gmail_app_password="pw",
            prospects=[good, bad], user_id=user.id, sender_name="김우진",
            daily_limit=10, min_delay=0, max_delay=0,
        )
        assert result["sent"] == 1
        assert result["skipped"] == 1
        assert sent[0]["to_email"] == "ok@corp.com"
        db_session.refresh(user)
        assert user.credits == start - 2  # 정상 1건만 과금
