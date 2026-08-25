"""발신 도메인 SPF/DKIM/DMARC 검사 테스트 (DNS는 모킹)."""
from app.services import dns_auth


class TestDomainAuth:
    def test_gmail_is_google_managed(self):
        r = dns_auth.check_domain_auth("someone@gmail.com")
        assert r["google_managed"] is True
        assert r["score"] == 100
        assert r["spf"]["status"] == "ok"

    def test_no_email(self):
        r = dns_auth.check_domain_auth(None)
        assert r["score"] == 0
        r2 = dns_auth.check_domain_auth("not-an-email")
        assert r2["score"] == 0

    def test_fully_authenticated_custom_domain(self, monkeypatch):
        def fake_txt(domain):
            if domain == "mycompany.com":
                return ["v=spf1 include:_spf.google.com ~all"]
            if domain == "_dmarc.mycompany.com":
                return ["v=DMARC1; p=reject; rua=mailto:d@mycompany.com"]
            if domain == "google._domainkey.mycompany.com":
                return ["v=DKIM1; k=rsa; p=MIGf..."]
            return []
        monkeypatch.setattr(dns_auth, "_txt_records", fake_txt)
        r = dns_auth.check_domain_auth("sales@mycompany.com")
        assert r["spf"]["status"] == "ok"
        assert r["dmarc"]["status"] == "ok"
        assert r["dkim"]["status"] == "ok"
        assert r["score"] == 100

    def test_missing_all(self, monkeypatch):
        monkeypatch.setattr(dns_auth, "_txt_records", lambda d: [])
        r = dns_auth.check_domain_auth("sales@bare.com")
        assert r["spf"]["status"] == "missing"
        assert r["dmarc"]["status"] == "missing"
        assert r["score"] < 40

    def test_spf_without_google_warns(self, monkeypatch):
        def fake_txt(domain):
            if domain == "other.com":
                return ["v=spf1 include:mailgun.org ~all"]
            return []
        monkeypatch.setattr(dns_auth, "_txt_records", fake_txt)
        r = dns_auth.check_domain_auth("x@other.com")
        assert r["spf"]["status"] == "warn"

    def test_dmarc_none_policy_warns(self, monkeypatch):
        def fake_txt(domain):
            if domain == "_dmarc.mon.com":
                return ["v=DMARC1; p=none"]
            return []
        monkeypatch.setattr(dns_auth, "_txt_records", fake_txt)
        r = dns_auth.check_domain_auth("x@mon.com")
        assert r["dmarc"]["status"] == "warn"

    def test_endpoint_requires_auth(self, client):
        assert client.get("/api/deliverability/domain-auth").status_code in (401, 403)
