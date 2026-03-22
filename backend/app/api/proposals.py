import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Activity, Proposal, ProposalTemplate, Prospect, User

router = APIRouter(tags=["proposals"])

proposal_router = APIRouter(prefix="/api/proposals")
template_router = APIRouter(prefix="/api/proposal-templates")


# ── Schemas ──

class ProposalCreate(BaseModel):
    prospect_id: int
    deal_id: Optional[int] = None
    title: str
    content_html: str
    total_amount: int = 0


class ProposalResponse(BaseModel):
    id: int
    prospect_id: int
    deal_id: Optional[int] = None
    title: str
    content_html: str
    total_amount: int
    status: str
    tracking_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    viewed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProposalTemplateCreate(BaseModel):
    name: str
    content_html: str


class ProposalTemplateResponse(BaseModel):
    id: int
    name: str
    content_html: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Proposals ──

@proposal_router.get("/", response_model=list[ProposalResponse])
def list_proposals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Proposal)
        .filter(Proposal.user_id == current_user.id)
        .order_by(Proposal.created_at.desc())
        .all()
    )


@proposal_router.post("/", response_model=ProposalResponse, status_code=status.HTTP_201_CREATED)
def create_proposal(
    req: ProposalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    proposal = Proposal(
        user_id=current_user.id,
        prospect_id=req.prospect_id,
        deal_id=req.deal_id,
        title=req.title,
        content_html=req.content_html,
        total_amount=req.total_amount,
        tracking_id=secrets.token_hex(16),
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


@proposal_router.put("/{proposal_id}", response_model=ProposalResponse)
def update_proposal(
    proposal_id: int,
    req: ProposalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id, Proposal.user_id == current_user.id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    proposal.title = req.title
    proposal.content_html = req.content_html
    proposal.total_amount = req.total_amount
    proposal.deal_id = req.deal_id
    db.commit()
    db.refresh(proposal)
    return proposal


@proposal_router.post("/{proposal_id}/send", response_model=ProposalResponse)
def send_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id, Proposal.user_id == current_user.id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    now = datetime.now(timezone.utc)
    proposal.status = "sent"
    proposal.sent_at = now

    activity = Activity(
        user_id=current_user.id,
        prospect_id=proposal.prospect_id,
        activity_type="proposal_sent",
        reference_id=proposal.id,
        description=f"제안서 발송: {proposal.title}",
    )
    db.add(activity)
    db.commit()
    db.refresh(proposal)
    return proposal


@proposal_router.delete("/{proposal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id, Proposal.user_id == current_user.id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    db.delete(proposal)
    db.commit()


# ── Public tracking endpoint (no auth) ──

@proposal_router.get("/view/{tracking_id}", response_class=HTMLResponse)
def view_proposal(
    tracking_id: str,
    db: Session = Depends(get_db),
):
    proposal = db.query(Proposal).filter(Proposal.tracking_id == tracking_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if not proposal.viewed_at:
        proposal.viewed_at = datetime.now(timezone.utc)
        proposal.status = "viewed"
        db.commit()

    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"><title>{proposal.title}</title>
    <style>body{{font-family:sans-serif;max-width:800px;margin:40px auto;padding:0 20px;}}</style>
    </head><body>
    <h1>{proposal.title}</h1>
    {proposal.content_html}
    <hr><p style="color:#999;font-size:12px;">총 금액: {proposal.total_amount:,}원</p>
    </body></html>
    """)


# ── Proposal Templates ──

@template_router.get("/", response_model=list[ProposalTemplateResponse])
def list_proposal_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(ProposalTemplate).filter(ProposalTemplate.user_id == current_user.id).all()


@template_router.post("/", response_model=ProposalTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_proposal_template(
    req: ProposalTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tmpl = ProposalTemplate(user_id=current_user.id, name=req.name, content_html=req.content_html)
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@template_router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_proposal_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tmpl = db.query(ProposalTemplate).filter(ProposalTemplate.id == template_id, ProposalTemplate.user_id == current_user.id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(tmpl)
    db.commit()
