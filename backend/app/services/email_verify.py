"""이메일 도메인 MX 검증 — 발송 전에 '받을 수 있는 메일함인지' DNS로 확인.

반송률(바운스)이 3%를 넘으면 Gmail이 계정 평판을 깎으므로,
잘못 추출된 이메일을 발송 전에 걸러내는 것이 발송 안전의 핵심이다.

- 수집 시: Prospect.email_valid 채움 (True/False/None=판정불가)
- 발송 시: email_valid=False 는 스킵 (크레딧도 안 씀)
- 전역 풀: 검증 결과가 GlobalProspect.email_validity_score 초기값에 반영
"""
import logging

logger = logging.getLogger(__name__)

# 도메인별 결과 캐시 (프로세스 생명주기 동안 유지 — 같은 도메인 반복 조회 방지)
_domain_cache: dict[str, bool | None] = {}

# 대형 메일 서비스는 MX 확인 생략 (항상 유효)
KNOWN_GOOD_DOMAINS = {
    "gmail.com", "naver.com", "daum.net", "hanmail.net", "kakao.com",
    "outlook.com", "hotmail.com", "yahoo.com", "nate.com", "icloud.com",
}


def check_email_domain(email: str | None) -> bool | None:
    """이메일 도메인에 MX(또는 A) 레코드가 있는지 확인.

    True = 수신 가능한 도메인, False = 존재하지 않는 도메인,
    None = 판정 불가 (DNS 오류/타임아웃 — 발송은 허용).
    """
    if not email or "@" not in email:
        return None
    domain = email.rsplit("@", 1)[1].strip().lower()
    if not domain or "." not in domain:
        return False
    if domain in KNOWN_GOOD_DOMAINS:
        return True
    if domain in _domain_cache:
        return _domain_cache[domain]

    result: bool | None
    try:
        import dns.resolver

        resolver = dns.resolver.Resolver()
        resolver.timeout = 3
        resolver.lifetime = 5
        try:
            answers = resolver.resolve(domain, "MX")
            result = len(answers) > 0
        except (dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            # MX 없어도 A 레코드로 수신하는 서버가 있음 (RFC 5321 fallback)
            try:
                resolver.resolve(domain, "A")
                result = True
            except Exception:
                result = False
        except dns.resolver.NXDOMAIN:
            result = False
    except Exception as e:
        logger.debug(f"MX check failed for {domain}: {e}")
        result = None  # 네트워크 문제 등 — 불이익 주지 않음

    _domain_cache[domain] = result
    return result
