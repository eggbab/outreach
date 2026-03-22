import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, UserSettings

router = APIRouter(prefix="/api/deliverability", tags=["deliverability"])


class DeliverabilityCheckRequest(BaseModel):
    subject: str = ""
    body: str = ""


class DeliverabilityResult(BaseModel):
    score: int  # 0-100, higher is better
    issues: list[str]
    suggestions: list[str]
    has_gmail: bool = False


SPAM_WORDS = [
    "무료", "공짜", "100%", "보장", "긴급", "지금 바로",
    "free", "guarantee", "urgent", "act now", "limited time",
    "click here", "buy now", "winner", "congratulations",
]


@router.post("/check", response_model=DeliverabilityResult)
def check_deliverability(
    req: DeliverabilityCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    issues = []
    suggestions = []
    score = 100

    # Check Gmail settings
    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    has_gmail = bool(settings and settings.gmail_email and settings.gmail_app_password_encrypted)
    if not has_gmail:
        issues.append("Gmail 설정이 완료되지 않았습니다")
        score -= 30

    text = f"{req.subject} {req.body}".lower()

    # Spam word check
    found_spam = [w for w in SPAM_WORDS if w.lower() in text]
    if found_spam:
        issues.append(f"스팸 키워드 감지: {', '.join(found_spam[:5])}")
        score -= min(len(found_spam) * 5, 25)

    # All caps check
    if req.subject and req.subject == req.subject.upper() and len(req.subject) > 5:
        issues.append("제목이 전체 대문자입니다")
        score -= 10

    # Excessive punctuation
    if re.search(r'[!?]{3,}', text):
        issues.append("과도한 느낌표/물음표 사용")
        score -= 10

    # Too short
    if len(req.body) < 50:
        issues.append("본문이 너무 짧습니다 (50자 미만)")
        score -= 10

    # Too long
    if len(req.body) > 5000:
        issues.append("본문이 너무 깁니다 (5000자 초과)")
        score -= 5

    # No unsubscribe mention
    if "수신거부" not in text and "unsubscribe" not in text:
        suggestions.append("수신거부 안내를 포함하면 스팸 점수가 낮아집니다")
        score -= 5

    # Suggestions
    if not req.subject:
        suggestions.append("제목을 입력해주세요")
    elif len(req.subject) > 100:
        suggestions.append("제목은 100자 이하로 작성하면 열람률이 높아집니다")

    if "{company_name}" not in req.body and "{name}" not in req.body:
        suggestions.append("개인화 변수({company_name})를 사용하면 응답률이 높아집니다")

    score = max(0, min(100, score))

    return DeliverabilityResult(
        score=score,
        issues=issues,
        suggestions=suggestions,
        has_gmail=has_gmail,
    )
