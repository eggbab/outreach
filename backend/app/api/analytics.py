from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    EmailLog, IndustryBenchmark,
    KeywordPerformance, Prospect, Project, User,
)
from app.services.collector.manager import _classify_industry

router = APIRouter(prefix="/api/projects/{project_id}/analytics", tags=["analytics"])


class EmailStatsResponse(BaseModel):
    total_sent: int = 0
    total_opened: int = 0
    total_clicked: int = 0
    open_rate: float = 0.0
    click_rate: float = 0.0


class DailyStatResponse(BaseModel):
    date: str
    sent: int = 0
    opened: int = 0
    clicked: int = 0


class FunnelResponse(BaseModel):
    collected: int = 0
    approved: int = 0
    email_sent: int = 0
    dm_sent: int = 0
    opened: int = 0
    clicked: int = 0


class ComparisonResponse(BaseModel):
    my_open_rate: float = 0.0
    my_click_rate: float = 0.0
    industry: str | None = None
    industry_avg_open_rate: float = 0.0
    industry_avg_click_rate: float = 0.0
    best_send_hour: int | None = None
    best_send_day: int | None = None


class KeywordRoiResponse(BaseModel):
    keyword_text: str
    source: str | None = None
    total_collected: int = 0
    total_emailed: int = 0
    total_opened: int = 0
    total_clicked: int = 0
    total_deals: int = 0
    total_deal_value: int = 0
    conversion_rate: float = 0.0
    roi_score: float = 0.0


class SourceRoiResponse(BaseModel):
    source: str
    total_collected: int = 0
    total_emailed: int = 0
    total_opened: int = 0
    total_deals: int = 0
    total_deal_value: int = 0
    avg_conversion_rate: float = 0.0


class RecommendationResponse(BaseModel):
    type: str
    title: str
    description: str
    impact: str


def _get_project_or_404(project_id: int, user_id: int, db: Session) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/email-stats", response_model=EmailStatsResponse)
def get_email_stats(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)

    from sqlalchemy import select
    prospect_ids = select(Prospect.id).where(Prospect.project_id == project_id)

    total_sent = (
        db.query(func.count(EmailLog.id))
        .filter(EmailLog.prospect_id.in_(prospect_ids), EmailLog.status == "success")
        .scalar() or 0
    )
    total_opened = (
        db.query(func.count(EmailLog.id))
        .filter(
            EmailLog.prospect_id.in_(prospect_ids),
            EmailLog.status == "success",
            EmailLog.opened_at.isnot(None),
        )
        .scalar() or 0
    )
    total_clicked = (
        db.query(func.count(EmailLog.id))
        .filter(
            EmailLog.prospect_id.in_(prospect_ids),
            EmailLog.status == "success",
            EmailLog.clicked_at.isnot(None),
        )
        .scalar() or 0
    )

    open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
    click_rate = (total_clicked / total_sent * 100) if total_sent > 0 else 0

    return EmailStatsResponse(
        total_sent=total_sent,
        total_opened=total_opened,
        total_clicked=total_clicked,
        open_rate=round(open_rate, 1),
        click_rate=round(click_rate, 1),
    )


@router.get("/email-stats/daily", response_model=list[DailyStatResponse])
def get_daily_email_stats(
    project_id: int,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)

    since = datetime.now(timezone.utc) - timedelta(days=days)
    from sqlalchemy import select
    prospect_ids = select(Prospect.id).where(Prospect.project_id == project_id)

    logs = (
        db.query(EmailLog)
        .filter(
            EmailLog.prospect_id.in_(prospect_ids),
            EmailLog.status == "success",
            EmailLog.sent_at >= since,
        )
        .all()
    )

    daily = {}
    for log in logs:
        day = log.sent_at.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"date": day, "sent": 0, "opened": 0, "clicked": 0}
        daily[day]["sent"] += 1
        if log.opened_at:
            daily[day]["opened"] += 1
        if log.clicked_at:
            daily[day]["clicked"] += 1

    return sorted(daily.values(), key=lambda x: x["date"])


@router.get("/funnel", response_model=FunnelResponse)
def get_funnel(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)

    collected = db.query(func.count(Prospect.id)).filter(Prospect.project_id == project_id).scalar() or 0
    approved = (
        db.query(func.count(Prospect.id))
        .filter(Prospect.project_id == project_id, Prospect.status.in_(["approved", "email_sent", "dm_sent"]))
        .scalar() or 0
    )
    email_sent = (
        db.query(func.count(Prospect.id))
        .filter(Prospect.project_id == project_id, Prospect.status == "email_sent")
        .scalar() or 0
    )
    dm_sent = (
        db.query(func.count(Prospect.id))
        .filter(Prospect.project_id == project_id, Prospect.status == "dm_sent")
        .scalar() or 0
    )

    from sqlalchemy import select
    prospect_ids = select(Prospect.id).where(Prospect.project_id == project_id)
    opened = (
        db.query(func.count(func.distinct(EmailLog.prospect_id)))
        .filter(EmailLog.prospect_id.in_(prospect_ids), EmailLog.opened_at.isnot(None))
        .scalar() or 0
    )
    clicked = (
        db.query(func.count(func.distinct(EmailLog.prospect_id)))
        .filter(EmailLog.prospect_id.in_(prospect_ids), EmailLog.clicked_at.isnot(None))
        .scalar() or 0
    )

    return FunnelResponse(
        collected=collected,
        approved=approved,
        email_sent=email_sent,
        dm_sent=dm_sent,
        opened=opened,
        clicked=clicked,
    )


@router.get("/comparison", response_model=ComparisonResponse)
def get_comparison(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)

    # Get project's main industry from most common category
    from sqlalchemy import select
    prospect_ids = select(Prospect.id).where(Prospect.project_id == project_id)

    total_sent = (
        db.query(func.count(EmailLog.id))
        .filter(EmailLog.prospect_id.in_(prospect_ids), EmailLog.status == "success")
        .scalar() or 0
    )
    total_opened = (
        db.query(func.count(EmailLog.id))
        .filter(EmailLog.prospect_id.in_(prospect_ids), EmailLog.status == "success", EmailLog.opened_at.isnot(None))
        .scalar() or 0
    )
    total_clicked = (
        db.query(func.count(EmailLog.id))
        .filter(EmailLog.prospect_id.in_(prospect_ids), EmailLog.status == "success", EmailLog.clicked_at.isnot(None))
        .scalar() or 0
    )

    my_open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
    my_click_rate = (total_clicked / total_sent * 100) if total_sent > 0 else 0

    # Find dominant category
    top_category = (
        db.query(Prospect.category, func.count(Prospect.id))
        .filter(Prospect.project_id == project_id, Prospect.category.isnot(None))
        .group_by(Prospect.category)
        .order_by(func.count(Prospect.id).desc())
        .first()
    )

    industry = _classify_industry(top_category[0]) if top_category else None
    industry_avg_open = 0.0
    industry_avg_click = 0.0
    best_hour = None
    best_day = None

    if industry:
        bm = db.query(IndustryBenchmark).filter(IndustryBenchmark.industry == industry).first()
        if bm:
            industry_avg_open = bm.avg_open_rate
            industry_avg_click = bm.avg_click_rate
            best_hour = bm.best_send_hour
            best_day = bm.best_send_day

    return ComparisonResponse(
        my_open_rate=round(my_open_rate, 1),
        my_click_rate=round(my_click_rate, 1),
        industry=industry,
        industry_avg_open_rate=industry_avg_open,
        industry_avg_click_rate=industry_avg_click,
        best_send_hour=best_hour,
        best_send_day=best_day,
    )


@router.get("/keyword-roi", response_model=list[KeywordRoiResponse])
def get_keyword_roi(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, current_user.id, db)

    from app.models.models import Keyword
    from sqlalchemy import select
    keyword_ids = select(Keyword.id).where(Keyword.project_id == project_id)

    perfs = (
        db.query(KeywordPerformance)
        .filter(
            KeywordPerformance.keyword_id.in_(keyword_ids),
            KeywordPerformance.user_id == current_user.id,
        )
        .order_by(KeywordPerformance.roi_score.desc())
        .all()
    )

    return [
        KeywordRoiResponse(
            keyword_text=p.keyword_text,
            source=p.source,
            total_collected=p.total_collected,
            total_emailed=p.total_emailed,
            total_opened=p.total_opened,
            total_clicked=p.total_clicked,
            total_deals=p.total_deals,
            total_deal_value=p.total_deal_value,
            conversion_rate=p.conversion_rate,
            roi_score=p.roi_score,
        )
        for p in perfs
    ]


@router.get("/source-roi", response_model=list[SourceRoiResponse])
def get_source_roi(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, current_user.id, db)

    from app.models.models import Keyword
    from sqlalchemy import select
    keyword_ids = select(Keyword.id).where(Keyword.project_id == project_id)

    perfs = (
        db.query(KeywordPerformance)
        .filter(
            KeywordPerformance.keyword_id.in_(keyword_ids),
            KeywordPerformance.user_id == current_user.id,
        )
        .all()
    )

    source_agg = {}
    for p in perfs:
        src = p.source or "unknown"
        if src not in source_agg:
            source_agg[src] = {
                "source": src, "total_collected": 0, "total_emailed": 0,
                "total_opened": 0, "total_deals": 0, "total_deal_value": 0,
            }
        s = source_agg[src]
        s["total_collected"] += p.total_collected
        s["total_emailed"] += p.total_emailed
        s["total_opened"] += p.total_opened
        s["total_deals"] += p.total_deals
        s["total_deal_value"] += p.total_deal_value

    result = []
    for s in source_agg.values():
        s["avg_conversion_rate"] = round(
            (s["total_deals"] / s["total_collected"]) if s["total_collected"] > 0 else 0, 4
        )
        result.append(SourceRoiResponse(**s))

    return sorted(result, key=lambda x: x.total_deal_value, reverse=True)


@router.get("/recommendations", response_model=list[RecommendationResponse])
def get_recommendations(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, current_user.id, db)
    recs = []

    from app.models.models import Keyword
    from sqlalchemy import select
    keyword_ids = select(Keyword.id).where(Keyword.project_id == project_id)

    perfs = (
        db.query(KeywordPerformance)
        .filter(
            KeywordPerformance.keyword_id.in_(keyword_ids),
            KeywordPerformance.user_id == current_user.id,
        )
        .order_by(KeywordPerformance.conversion_rate.desc())
        .all()
    )

    # 1. Top converting keywords
    high_conv = [p for p in perfs if p.conversion_rate > 0 and p.total_collected >= 5]
    if high_conv:
        top = high_conv[0]
        recs.append(RecommendationResponse(
            type="keyword",
            title=f"'{top.keyword_text}' 키워드에 집중하세요",
            description=f"이 키워드는 {top.conversion_rate*100:.1f}% 전환율로 가장 높은 성과를 보이고 있습니다. 이 키워드로 더 많은 잠재고객을 수집해보세요.",
            impact="high",
        ))

    # 2. Source comparison
    source_data = {}
    for p in perfs:
        src = p.source or "unknown"
        if src not in source_data:
            source_data[src] = {"collected": 0, "deals": 0, "value": 0}
        source_data[src]["collected"] += p.total_collected
        source_data[src]["deals"] += p.total_deals
        source_data[src]["value"] += p.total_deal_value

    if len(source_data) >= 2:
        best_source = max(source_data.items(), key=lambda x: x[1]["value"])
        if best_source[1]["value"] > 0:
            recs.append(RecommendationResponse(
                type="source",
                title=f"'{best_source[0]}' 소스가 가장 수익성이 높습니다",
                description=f"총 {best_source[1]['value']:,}원의 매출을 생성했습니다. 이 소스를 우선적으로 활용하세요.",
                impact="high",
            ))

    # 3. Best send timing from benchmarks
    top_category = (
        db.query(Prospect.category, func.count(Prospect.id))
        .filter(Prospect.project_id == project_id, Prospect.category.isnot(None))
        .group_by(Prospect.category)
        .order_by(func.count(Prospect.id).desc())
        .first()
    )
    if top_category:
        industry = _classify_industry(top_category[0])
        if industry:
            bm = db.query(IndustryBenchmark).filter(IndustryBenchmark.industry == industry).first()
            if bm and bm.best_send_hour is not None:
                day_names = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
                day_str = day_names[bm.best_send_day] if bm.best_send_day is not None else ""
                recs.append(RecommendationResponse(
                    type="timing",
                    title=f"최적 발송 시간: {day_str} {bm.best_send_hour}시",
                    description=f"{industry} 업종에서 이 시간대에 가장 높은 이메일 오픈율을 기록하고 있습니다.",
                    impact="medium",
                ))

    # 4. Low-performing keywords warning
    low_perf = [p for p in perfs if p.total_collected >= 10 and p.total_opened == 0 and p.total_emailed > 0]
    if low_perf:
        recs.append(RecommendationResponse(
            type="keyword",
            title=f"성과 낮은 키워드 {len(low_perf)}개 발견",
            description="수집은 되었지만 이메일 열람이 없는 키워드가 있습니다. 이 키워드를 재검토하거나 이메일 제목을 수정해보세요.",
            impact="low",
        ))

    return recs
