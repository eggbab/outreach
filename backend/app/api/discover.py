from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.plans import increment_usage
from app.core.security import get_current_user
from app.models.models import GlobalProspect, Prospect, User

router = APIRouter(prefix="/api/discover", tags=["discover"])

# Discover는 크레딧 소모 없이 열람 가능 (이메일은 마스킹, import 시 크레딧 차감)


def _mask_email(email: str | None) -> str | None:
    if not email:
        return None
    parts = email.split("@")
    if len(parts) != 2:
        return email
    local = parts[0]
    if len(local) <= 1:
        return f"*@{parts[1]}"
    return f"{local[0]}{'*' * (len(local) - 1)}@{parts[1]}"


class DiscoverItemResponse(BaseModel):
    id: int
    company_name: str | None = None
    email_masked: str | None = None
    industry: str | None = None
    region: str | None = None
    validity_score: float = 0.0
    times_collected: int = 0
    times_opened: int = 0
    times_replied: int = 0
    last_verified_at: str | None = None
    source: str | None = None

    model_config = {"from_attributes": True}


class DiscoverListResponse(BaseModel):
    items: list[DiscoverItemResponse]
    total: int
    total_pages: int


class DiscoverStatsResponse(BaseModel):
    total_prospects: int
    by_industry: list[dict]
    by_region: list[dict]


class ImportRequest(BaseModel):
    global_prospect_ids: list[int]
    project_id: int


@router.get("/", response_model=DiscoverListResponse)
def discover_prospects(
    q: str | None = None,
    industry: str | None = None,
    region: str | None = None,
    has_email: bool | None = None,
    min_validity: float | None = None,
    sort: str = Query("popular", pattern="^(popular|quality)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(GlobalProspect)

    if q:
        query = query.filter(
            GlobalProspect.company_name.ilike(f"%{q}%")
            | GlobalProspect.category.ilike(f"%{q}%")
        )
    if industry:
        query = query.filter(GlobalProspect.industry == industry)
    if region:
        query = query.filter(GlobalProspect.region == region)
    if has_email:
        query = query.filter(GlobalProspect.email.isnot(None), GlobalProspect.email != "")
    if min_validity is not None:
        query = query.filter(GlobalProspect.email_validity_score >= min_validity)

    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)

    if sort == "quality":
        # 반응 데이터 기반 품질 순 — 답장 > 검증 점수 > 열람 (데이터 해자의 노출면)
        order = (
            GlobalProspect.times_replied.desc(),
            GlobalProspect.email_validity_score.desc(),
            GlobalProspect.times_opened.desc(),
        )
    else:
        order = (GlobalProspect.times_collected.desc(),)

    gps = (
        query.order_by(*order)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        DiscoverItemResponse(
            id=gp.id,
            company_name=gp.company_name,
            email_masked=_mask_email(gp.email),
            industry=gp.industry,
            region=gp.region,
            validity_score=gp.email_validity_score,
            times_collected=gp.times_collected,
            times_opened=gp.times_opened or 0,
            times_replied=gp.times_replied or 0,
            last_verified_at=gp.last_verified_at.isoformat() if gp.last_verified_at else None,
            source=gp.source,
        )
        for gp in gps
    ]

    return DiscoverListResponse(items=items, total=total, total_pages=total_pages)


@router.get("/stats", response_model=DiscoverStatsResponse)
def discover_stats(db: Session = Depends(get_db)):
    """Public endpoint for marketing — no auth required."""
    total = db.query(func.count(GlobalProspect.id)).scalar() or 0

    by_industry_rows = (
        db.query(GlobalProspect.industry, func.count(GlobalProspect.id))
        .filter(GlobalProspect.industry.isnot(None))
        .group_by(GlobalProspect.industry)
        .order_by(func.count(GlobalProspect.id).desc())
        .all()
    )
    by_industry = [{"industry": row[0], "count": row[1]} for row in by_industry_rows]

    by_region_rows = (
        db.query(GlobalProspect.region, func.count(GlobalProspect.id))
        .filter(GlobalProspect.region.isnot(None))
        .group_by(GlobalProspect.region)
        .order_by(func.count(GlobalProspect.id).desc())
        .all()
    )
    by_region = [{"region": row[0], "count": row[1]} for row in by_region_rows]

    return DiscoverStatsResponse(
        total_prospects=total,
        by_industry=by_industry,
        by_region=by_region,
    )


@router.post("/import")
def import_prospects(
    req: ImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check credits
    from app.core.plans import check_credits
    count = len(req.global_prospect_ids)
    credit_check = check_credits(db, current_user.id, "prospect", count)
    if not credit_check["allowed"]:
        raise HTTPException(
            status_code=402,
            detail=f"크레딧이 부족합니다. (필요: {credit_check['cost']}, 잔액: {credit_check['balance']})",
        )

    # Verify project ownership
    from app.models.models import Project
    project = (
        db.query(Project)
        .filter(Project.id == req.project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    imported = 0
    for gp_id in req.global_prospect_ids:
        gp = db.query(GlobalProspect).filter(GlobalProspect.id == gp_id).first()
        if not gp:
            continue

        # Check if already imported
        existing = (
            db.query(Prospect)
            .filter(Prospect.project_id == req.project_id, Prospect.global_prospect_id == gp_id)
            .first()
        )
        if existing:
            continue

        prospect = Prospect(
            project_id=req.project_id,
            name=gp.company_name,
            email=gp.email,
            phone=gp.phone,
            instagram=gp.instagram,
            website=gp.website,
            source=gp.source,
            category=gp.category,
            global_prospect_id=gp.id,
            status="collected",
        )
        db.add(prospect)
        imported += 1

    if imported > 0:
        # 실제 가져온 건수만큼 크레딧 차감 (수집 1건 = 1cr)
        from app.core.plans import CREDIT_COSTS, deduct_credits
        remaining = deduct_credits(
            db, current_user.id, CREDIT_COSTS["prospect"] * imported,
            f"잠재고객 DB에서 {imported}건 가져오기",
        )
        if remaining is None:
            db.rollback()
            raise HTTPException(status_code=402, detail="크레딧이 부족합니다.")
        increment_usage(db, current_user.id, "prospects_collected", imported)
    db.commit()
    return {"message": f"{imported}건의 잠재고객을 가져왔습니다", "imported": imported}
