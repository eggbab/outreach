from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import EmailLog, EmailTemplate, EmailVariant, User

router = APIRouter(prefix="/api/templates", tags=["templates"])


class TemplateCreate(BaseModel):
    name: str
    subject: str
    body: str


class TemplateResponse(BaseModel):
    id: int
    name: str
    subject: str
    body: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VariantCreate(BaseModel):
    variant_name: str = "A"
    subject: str
    body: str
    weight: int = 50


class VariantResponse(BaseModel):
    id: int
    template_id: int
    variant_name: str
    subject: str
    body: str
    weight: int

    model_config = {"from_attributes": True}


class VariantStatsResponse(BaseModel):
    variant_id: int
    variant_name: str
    sent: int = 0
    opened: int = 0
    clicked: int = 0
    open_rate: float = 0.0
    click_rate: float = 0.0


@router.get("/", response_model=list[TemplateResponse])
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(EmailTemplate)
        .filter(EmailTemplate.user_id == current_user.id)
        .order_by(EmailTemplate.updated_at.desc())
        .all()
    )


@router.post("/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    req: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = EmailTemplate(
        user_id=current_user.id,
        name=req.name,
        subject=req.subject,
        body=req.body,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = (
        db.query(EmailTemplate)
        .filter(EmailTemplate.id == template_id, EmailTemplate.user_id == current_user.id)
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int,
    req: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = (
        db.query(EmailTemplate)
        .filter(EmailTemplate.id == template_id, EmailTemplate.user_id == current_user.id)
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    template.name = req.name
    template.subject = req.subject
    template.body = req.body
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = (
        db.query(EmailTemplate)
        .filter(EmailTemplate.id == template_id, EmailTemplate.user_id == current_user.id)
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(template)
    db.commit()


# ── Variants ──

@router.get("/{template_id}/variants", response_model=list[VariantResponse])
def list_variants(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = (
        db.query(EmailTemplate)
        .filter(EmailTemplate.id == template_id, EmailTemplate.user_id == current_user.id)
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return db.query(EmailVariant).filter(EmailVariant.template_id == template_id).all()


@router.post("/{template_id}/variants", response_model=VariantResponse, status_code=status.HTTP_201_CREATED)
def create_variant(
    template_id: int,
    req: VariantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = (
        db.query(EmailTemplate)
        .filter(EmailTemplate.id == template_id, EmailTemplate.user_id == current_user.id)
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    variant = EmailVariant(
        template_id=template_id,
        variant_name=req.variant_name,
        subject=req.subject,
        body=req.body,
        weight=req.weight,
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


@router.delete("/{template_id}/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_variant(
    template_id: int,
    variant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    variant = (
        db.query(EmailVariant)
        .filter(EmailVariant.id == variant_id, EmailVariant.template_id == template_id)
        .first()
    )
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    db.delete(variant)
    db.commit()


@router.get("/{template_id}/variants/stats", response_model=list[VariantStatsResponse])
def get_variant_stats(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = (
        db.query(EmailTemplate)
        .filter(EmailTemplate.id == template_id, EmailTemplate.user_id == current_user.id)
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    variants = db.query(EmailVariant).filter(EmailVariant.template_id == template_id).all()
    results = []
    for v in variants:
        sent = db.query(func.count(EmailLog.id)).filter(EmailLog.variant_id == v.id, EmailLog.status == "success").scalar() or 0
        opened = db.query(func.count(EmailLog.id)).filter(EmailLog.variant_id == v.id, EmailLog.opened_at.isnot(None)).scalar() or 0
        clicked = db.query(func.count(EmailLog.id)).filter(EmailLog.variant_id == v.id, EmailLog.clicked_at.isnot(None)).scalar() or 0
        results.append(VariantStatsResponse(
            variant_id=v.id,
            variant_name=v.variant_name,
            sent=sent,
            opened=opened,
            clicked=clicked,
            open_rate=round((opened / sent * 100) if sent > 0 else 0, 1),
            click_rate=round((clicked / sent * 100) if sent > 0 else 0, 1),
        ))
    return results
