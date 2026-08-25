"""발신 도메인 이메일 인증(SPF/DKIM/DMARC) DNS 검사.

콜드 아웃리치에서 인증이 없으면 Gmail·네이버가 스팸함으로 보낸다.
Gmail(개인 @gmail.com)로 보내면 구글이 알아서 인증하지만, 커스텀 도메인
(예: sales@mycompany.com)을 Gmail로 연결해 보내는 경우 SPF에 google을 include하고
DKIM/DMARC를 설정해야 도달률이 크게 오른다.

dnspython으로 실제 DNS 레코드를 조회한다(email_verify와 동일 의존성).
"""
import logging

logger = logging.getLogger(__name__)

# @gmail.com 자체는 구글이 관리 — 별도 인증 불필요
_GOOGLE_MANAGED = {"gmail.com", "googlemail.com"}


def _txt_records(domain: str) -> list[str]:
    try:
        import dns.resolver

        resolver = dns.resolver.Resolver()
        resolver.timeout = 3
        resolver.lifetime = 5
        answers = resolver.resolve(domain, "TXT")
        out = []
        for r in answers:
            # TXT는 여러 문자열로 쪼개질 수 있어 합침
            val = "".join(
                s.decode() if isinstance(s, bytes) else str(s)
                for s in getattr(r, "strings", [str(r)])
            )
            out.append(val.strip('"'))
        return out
    except Exception as e:
        logger.debug(f"TXT lookup failed for {domain}: {e}")
        return []


def check_domain_auth(email: str | None) -> dict:
    """발신 이메일 도메인의 SPF/DKIM/DMARC 상태를 반환.

    반환: {
      domain, google_managed, spf, dkim, dmarc: {status, detail},
      score(0-100), summary
    }
    status: "ok" | "warn" | "missing" | "unknown"
    """
    result = {
        "domain": None, "google_managed": False,
        "spf": {"status": "unknown", "detail": ""},
        "dkim": {"status": "unknown", "detail": ""},
        "dmarc": {"status": "unknown", "detail": ""},
        "score": 0, "summary": "",
    }
    if not email or "@" not in email:
        result["summary"] = "이메일 주소가 없습니다."
        return result

    domain = email.rsplit("@", 1)[1].strip().lower()
    result["domain"] = domain

    if domain in _GOOGLE_MANAGED:
        result["google_managed"] = True
        for k in ("spf", "dkim", "dmarc"):
            result[k] = {"status": "ok", "detail": "Google이 관리하는 도메인 — 자동 인증됨"}
        result["score"] = 100
        result["summary"] = "@gmail.com은 구글이 인증을 자동 처리합니다. 별도 설정 불필요."
        return result

    # 커스텀 도메인 — 실제 레코드 조회
    txts = _txt_records(domain)

    # SPF: v=spf1 ... (google include 권장)
    spf = next((t for t in txts if t.lower().startswith("v=spf1")), None)
    if spf:
        if "include:_spf.google.com" in spf.lower() or "google.com" in spf.lower():
            result["spf"] = {"status": "ok", "detail": "SPF에 Google이 포함됨"}
        else:
            result["spf"] = {"status": "warn", "detail": "SPF는 있으나 Google include 없음 — Gmail 발송 시 실패 위험"}
    else:
        result["spf"] = {"status": "missing", "detail": "SPF 레코드 없음"}

    # DMARC: _dmarc.<domain> TXT v=DMARC1
    dmarc_txts = _txt_records(f"_dmarc.{domain}")
    dmarc = next((t for t in dmarc_txts if t.lower().startswith("v=dmarc1")), None)
    if dmarc:
        policy = "none"
        for part in dmarc.split(";"):
            part = part.strip().lower()
            if part.startswith("p="):
                policy = part[2:].strip()
        if policy in ("quarantine", "reject"):
            result["dmarc"] = {"status": "ok", "detail": f"DMARC 정책: {policy}"}
        else:
            result["dmarc"] = {"status": "warn", "detail": "DMARC 있으나 정책이 none — 모니터링만 됨"}
    else:
        result["dmarc"] = {"status": "missing", "detail": "DMARC 레코드 없음"}

    # DKIM: 셀렉터를 모르면 확정 불가. Google Workspace 기본 셀렉터 google._domainkey 확인
    dkim_txts = _txt_records(f"google._domainkey.{domain}")
    if any("v=dkim1" in t.lower() or "p=" in t.lower() for t in dkim_txts):
        result["dkim"] = {"status": "ok", "detail": "Google DKIM 셀렉터 확인됨"}
    else:
        result["dkim"] = {"status": "warn",
                          "detail": "Google DKIM 셀렉터 미확인 (다른 셀렉터일 수 있음)"}

    # 점수화
    weights = {"ok": 1.0, "warn": 0.5, "missing": 0.0, "unknown": 0.0}
    score = int(sum(weights[result[k]["status"]] for k in ("spf", "dkim", "dmarc")) / 3 * 100)
    result["score"] = score

    ok = [k.upper() for k in ("spf", "dkim", "dmarc") if result[k]["status"] == "ok"]
    if score >= 80:
        result["summary"] = f"인증 양호 ({', '.join(ok)}). 도달률에 유리합니다."
    elif score >= 40:
        result["summary"] = "일부 인증이 설정되지 않았습니다. 도달률 개선을 위해 SPF/DKIM/DMARC를 완성하세요."
    else:
        result["summary"] = "이메일 인증이 거의 없습니다. 커스텀 도메인 발송 시 스팸함 위험이 높습니다."
    return result
