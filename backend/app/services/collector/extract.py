"""
Deep email/phone extraction — 사이트에서 이메일을 최대한 찾아오는 공통 모듈.

전략 (순서대로 시도, 이메일 찾으면 즉시 반환):
1. 메인 페이지 텍스트 + mailto 링크
2. 페이지 내 연락처/회사소개 링크 자동 탐색
3. 공통 하위 경로 (/contact, /about, /문의 등)
4. footer 영역 집중 탐색
5. 도메인 기반 추측 (info@, contact@ 등) — DNS MX 레코드 확인
"""
import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}(?![a-zA-Z0-9])")
PHONE_REGEX = re.compile(r"0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}")
# 인스타 핸들 — 사이트 본문/링크에서 추출
INSTAGRAM_URL_REGEX = re.compile(r"instagram\.com/([a-zA-Z0-9_.]{1,30})")
INSTAGRAM_BLACKLIST = {
    "p", "reel", "explore", "stories", "tv", "tags", "accounts", "about", "directory",
    # 플랫폼/서비스 공식 계정 — 업체 계정으로 오인 방지
    "catchtable_official", "naver_official", "instagram", "kakao_official",
    "baemin_official", "yogiyo_official", "coupang", "tablingofficial",
}


def normalize_instagram(raw: str | None) -> str | None:
    """@handle / URL / 대소문자 혼재를 순수 소문자 핸들로 정규화. 유효하지 않으면 None.

    수집·수동입력·DM 큐 전 경로에서 동일하게 사용해 dedup·발송 일관성을 보장한다.
    """
    if not raw:
        return None
    h = raw.strip()
    if "instagram.com/" in h:
        h = h.split("instagram.com/")[-1]
    h = h.split("/")[0].split("?")[0].strip().lstrip("@").strip(".").lower()
    if not h or len(h) > 30:
        return None
    if h in INSTAGRAM_BLACKLIST:
        return None
    if not re.fullmatch(r"[a-z0-9_.]{1,30}", h):
        return None
    if re.search(r"\.(kr|com|net|org|io|co|me|shop)$", h):
        return None
    return h


def keyword_matches(page_title: str, page_text: str, keyword: str, level: str = "medium") -> bool:
    """
    수집 결과 페이지가 키워드와 얼마나 잘 맞는지 판정.

    level:
      loose  — 검색엔진이 준 결과 그대로 (필터링 없음, 양 ↑ 정확도 ↓)
      medium — 페이지 본문 또는 제목에 키워드 일부라도 포함 (권장)
      strict — 제목에도 본문에도 키워드 포함 + 키워드의 모든 단어가 본문에 등장
    """
    if level == "loose":
        return True
    title_l = (page_title or "").lower()
    text_l = (page_text or "")[:5000].lower()  # 본문 앞 5KB만 검사 (성능)
    kw_l = (keyword or "").lower().strip()
    if not kw_l:
        return True

    if level == "medium":
        return (kw_l in title_l) or (kw_l in text_l)

    # strict — 모든 단어가 본문에 등장 + 제목 또는 본문에 통째 키워드도 포함
    words = [w for w in kw_l.split() if len(w) >= 2]
    if not words:
        return False
    all_words_in_text = all(w in text_l for w in words)
    full_phrase_present = (kw_l in title_l) or (kw_l in text_l)
    return all_words_in_text and full_phrase_present

EXCLUDED_EMAIL_DOMAINS = {
    "naver.com", "daum.net", "hanmail.net", "kakao.com", "gmail.com",
    "nate.com", "yahoo.com", "yahoo.co.kr", "hotmail.com", "outlook.com",
    "example.com", "tistory.com", "google.com", "test.com", "wixpress.com",
    "sentry.io", "w3.org", "schema.org", "googleapis.com", "gstatic.com",
}

# 연락처 페이지로 이어질 가능성이 높은 링크 텍스트
CONTACT_LINK_PATTERNS = re.compile(
    r"(contact|문의|연락|회사소개|about|company|오시는|찾아오|인사말|소개|support|help|inquiry|상담)",
    re.IGNORECASE,
)

# 공통 하위 경로
CONTACT_PATHS = [
    "/contact", "/contact-us", "/about", "/about-us", "/company",
    "/info", "/support", "/inquiry", "/help",
    # 한국어 경로
    "/문의", "/회사소개", "/소개", "/연락처", "/상담",
    # CMS 패턴
    "/page/contact", "/pages/about", "/bbs/contact",
]


def _filter_emails(raw_emails: set[str]) -> list[str]:
    """이메일 필터링 — 제외 도메인, 너무 긴 것, 이미지 확장자 등 제거"""
    result = []
    for e in raw_emails:
        e = e.lower().strip(".")
        if len(e) > 100:
            continue
        domain = e.split("@")[-1]
        if domain in EXCLUDED_EMAIL_DOMAINS:
            continue
        # 이미지/파일 확장자로 끝나면 제외 (ooo@2x.png 같은 거)
        if re.search(r"\.(png|jpg|gif|svg|css|js)$", e):
            continue
        result.append(e)
    return result


def _extract_instagram_handles(page) -> list[str]:
    """페이지에서 인스타 핸들 추출 — 링크의 instagram.com/USERNAME 패턴."""
    try:
        hrefs = page.eval_on_selector_all(
            "a[href*='instagram.com']",
            "els => els.map(el => el.href)",
        )
    except Exception:
        return []
    handles = set()
    for href in hrefs:
        m = INSTAGRAM_URL_REGEX.search(href or "")
        if m:
            h = m.group(1).strip(".").lower()
            if not h or h in INSTAGRAM_BLACKLIST or len(h) > 30:
                continue
            # 도메인이 핸들로 오인되는 경우 제외 (예: 공유 링크의 ppss.kr)
            if re.search(r"\.(kr|com|net|org|io|co|me|shop)$", h):
                continue
            handles.add(h)
    return list(handles)


def _extract_from_page(page, url: str) -> tuple[list[str], list[str], list[str]]:
    """단일 페이지에서 이메일 + 전화번호 + 인스타 핸들 추출."""
    try:
        page.goto(url, timeout=12000, wait_until="domcontentloaded")
        page.wait_for_timeout(800)
    except Exception:
        return [], [], []

    try:
        # 1) 본문 텍스트에서 추출
        text = page.text_content("body") or ""
        emails = set(EMAIL_REGEX.findall(text))
        phones = set(PHONE_REGEX.findall(text))
        handles = _extract_instagram_handles(page)

        # 2) mailto: 링크에서 추출 (텍스트에 안 보이는 이메일도 잡힘)
        mailto_emails = page.eval_on_selector_all(
            "a[href^='mailto:']",
            "els => els.map(el => el.href.replace('mailto:', '').split('?')[0])",
        )
        emails.update(mailto_emails)

        # 3) HTML 속성에서 추출 (data-email, value 등)
        hidden_emails = page.evaluate("""
            () => {
                const found = [];
                document.querySelectorAll('[data-email], [data-mail], input[type=hidden]').forEach(el => {
                    const v = el.getAttribute('data-email') || el.getAttribute('data-mail') || el.value || '';
                    if (v.includes('@')) found.push(v);
                });
                return found;
            }
        """)
        emails.update(hidden_emails)

        return _filter_emails(emails), list(phones), handles
    except Exception:
        return [], [], []


def _find_contact_links(page, base_url: str) -> list[str]:
    """현재 페이지에서 연락처/회사소개 관련 링크를 찾아 반환"""
    try:
        links = page.eval_on_selector_all(
            "a[href]",
            """(els) => els.map(el => ({
                href: el.href,
                text: (el.textContent || '').trim().slice(0, 50)
            }))""",
        )
        result = []
        seen = set()
        for link in links:
            href = link.get("href", "")
            text = link.get("text", "")
            if not href.startswith("http"):
                continue
            # 같은 도메인만
            if urlparse(href).netloc != urlparse(base_url).netloc:
                continue
            if href in seen:
                continue
            if CONTACT_LINK_PATTERNS.search(text) or CONTACT_LINK_PATTERNS.search(href):
                seen.add(href)
                result.append(href)
        return result[:5]  # 최대 5개
    except Exception:
        return []


def deep_extract_email(page, site_url: str) -> tuple[str | None, str | None, str | None, str | None]:
    """
    사이트에서 이메일/전화/인스타 핸들/회사명을 최대한 찾아오기.

    Returns: (email, phone, company_name, instagram_handle)
    """
    parsed = urlparse(site_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    domain = parsed.netloc.replace("www.", "")

    # 회사명: 도메인에서 추출
    company_name = domain.split(".")[0] if domain else None

    # ── 1단계: 메인 페이지
    emails, phones, handles = _extract_from_page(page, site_url)
    insta = handles[0] if handles else None
    if emails:
        return emails[0], phones[0] if phones else None, company_name, insta

    # ── 2단계: 메인 페이지의 <title>에서 회사명 추출
    try:
        title = page.title() or ""
        if title and len(title) < 60:
            company_name = title.split("|")[0].split("-")[0].split("::")[0].strip() or company_name
    except Exception:
        pass

    # ── 3단계: 페이지 내 연락처 링크 자동 탐색
    contact_links = _find_contact_links(page, base)
    for link in contact_links:
        emails, link_phones, link_handles = _extract_from_page(page, link)
        insta = insta or (link_handles[0] if link_handles else None)
        if emails:
            return emails[0], (phones or link_phones or [None])[0], company_name, insta

    # ── 4단계: 공통 하위 경로 시도
    for path in CONTACT_PATHS:
        url = base + path
        emails, path_phones, path_handles = _extract_from_page(page, url)
        insta = insta or (path_handles[0] if path_handles else None)
        if emails:
            return emails[0], (phones or path_phones or [None])[0], company_name, insta

    # ── 5단계: footer 영역만 집중 추출
    try:
        page.goto(site_url, timeout=10000, wait_until="domcontentloaded")
        page.wait_for_timeout(500)
        footer_text = page.eval_on_selector_all(
            "footer, [class*='footer'], [id*='footer'], [class*='bottom']",
            "els => els.map(el => el.textContent || '').join(' ')",
        )
        if footer_text:
            footer_emails = _filter_emails(set(EMAIL_REGEX.findall(footer_text)))
            if footer_emails:
                return footer_emails[0], phones[0] if phones else None, company_name, insta
    except Exception:
        pass

    # 이메일 못 찾음 — 인스타라도 있으면 반환
    return None, phones[0] if phones else None, company_name, insta
