"""DM 메시지 조립 — 변수 치환 + 스핀택스 변형 (안티밴 핵심).

인스타는 동일 문구 대량 발송을 스팸으로 감지한다. 매 수신자마다 문구를
조금씩 다르게 만들어 기계적 패턴을 깬다.

두 가지 변형:
1. 스핀택스: `{안녕하세요|반갑습니다|안녕하십니까}` → 셋 중 하나 랜덤 선택
2. 자동 인사말/마무리: 템플릿에 스핀택스가 없어도 앞뒤에 변형된 인사를 붙임

deterministic 시드(prospect_id)로 변형 → 같은 대상엔 항상 같은 문구
(재발송/미리보기 일관성). random 모듈을 안 써서 워크플로/테스트에서도 안정적.
"""
import re

_SPINTAX_RE = re.compile(r"\{([^{}]+)\}")

# 자동 인사말/마무리 풀 — 템플릿에 명시적 스핀택스가 없을 때 다양성 부여
_GREETINGS = [
    "안녕하세요", "안녕하세요!", "반갑습니다", "안녕하십니까",
]
_CLOSINGS = [
    "감사합니다.", "회신 기다리겠습니다. 감사합니다.", "좋은 하루 되세요.",
    "긍정적인 검토 부탁드립니다.", "감사합니다!",
]


def _pick(options: list[str], seed: int) -> str:
    return options[seed % len(options)]


def expand_spintax(text: str, seed: int) -> str:
    """`{a|b|c}` 패턴을 seed 기반으로 하나씩 치환. 이메일·DM 공용."""
    return _expand_spintax(text, seed)


def _expand_spintax(text: str, seed: int) -> str:
    """`{a|b|c}` 패턴을 seed 기반으로 하나씩 치환. 중첩 없음 가정."""
    counter = [seed]

    def repl(m):
        parts = m.group(1).split("|")
        counter[0] = counter[0] * 31 + 7  # seed를 진행시켜 옵션마다 다른 선택
        return parts[counter[0] % len(parts)].strip()

    # 여러 스핀택스 그룹을 각각 다른 선택으로
    prev = None
    out = text
    while prev != out:
        prev = out
        out = _SPINTAX_RE.sub(repl, out, count=1)
    return out


def render_dm(template: str, *, company_name: str = "", username: str = "",
              prospect_id: int = 0, auto_vary: bool = True) -> str:
    """DM 최종 문구 생성.

    변수: {company}, {company_name}, {name}, {username}
    스핀택스: {옵션1|옵션2|...}
    auto_vary=True면 스핀택스가 전혀 없는 템플릿에 인사말/마무리 변형을 덧붙임.
    """
    name = company_name or username or "담당자"
    msg = template or ""

    # 변수 치환 (스핀택스보다 먼저 — 변수값에 | 가 있어도 안전하도록 이스케이프 불필요)
    for token in ("{company_name}", "{company}", "{name}"):
        msg = msg.replace(token, name)
    msg = msg.replace("{username}", username or "")

    had_spintax = bool(_SPINTAX_RE.search(msg))
    msg = _expand_spintax(msg, prospect_id or 1)

    if auto_vary and not had_spintax:
        # 명시적 변형이 없으면 인사말을 앞에, 마무리를 뒤에 자동 추가 (중복 방지)
        greeting = _pick(_GREETINGS, prospect_id or 1)
        closing = _pick(_CLOSINGS, (prospect_id or 1) * 3)
        stripped = msg.strip()
        if not stripped.startswith(("안녕", "반갑")):
            stripped = f"{greeting} {name}님, {stripped}"
        if not stripped.endswith(("감사합니다.", "감사합니다!", "하세요.", "드립니다.")):
            stripped = f"{stripped}\n\n{closing}"
        msg = stripped

    return msg.strip()
