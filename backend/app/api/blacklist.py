from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Blacklist, User

router = APIRouter(prefix="/api/blacklist", tags=["blacklist"])


class BlacklistCreate(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    instagram: Optional[str] = None
    company_name: Optional[str] = None
    reason: Optional[str] = None


class BlacklistResponse(BaseModel):
    id: int
    email: Optional[str] = None
    phone: Optional[str] = None
    instagram: Optional[str] = None
    company_name: Optional[str] = None
    reason: Optional[str] = None

    model_config = {"from_attributes": True}


class BlacklistCheckRequest(BaseModel):
    emails: list[str] = []
    instagrams: list[str] = []


class BlacklistCheckResponse(BaseModel):
    blacklisted_emails: list[str] = []
    blacklisted_instagrams: list[str] = []


@router.get("/", response_model=list[BlacklistResponse])
def list_blacklist(
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Blacklist).filter(Blacklist.user_id == current_user.id)
    if q:
        search = f"%{q}%"
        query = query.filter(
            or_(
                Blacklist.company_name.ilike(search),
                Blacklist.email.ilike(search),
                Blacklist.instagram.ilike(search),
            )
        )
    return query.order_by(Blacklist.created_at.desc()).all()


@router.post("/", response_model=BlacklistResponse)
def add_to_blacklist(
    req: BlacklistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not req.email and not req.phone and not req.instagram and not req.company_name:
        raise HTTPException(status_code=400, detail="최소 하나의 연락처 정보를 입력해주세요.")

    entry = Blacklist(
        user_id=current_user.id,
        email=req.email,
        phone=req.phone,
        instagram=req.instagram,
        company_name=req.company_name,
        reason=req.reason,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{blacklist_id}")
def remove_from_blacklist(
    blacklist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = (
        db.query(Blacklist)
        .filter(Blacklist.id == blacklist_id, Blacklist.user_id == current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="블랙리스트 항목을 찾을 수 없습니다.")
    db.delete(entry)
    db.commit()
    return {"message": "블랙리스트에서 삭제되었습니다."}


@router.post("/check", response_model=BlacklistCheckResponse)
def check_blacklist(
    req: BlacklistCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    blacklisted_emails = []
    blacklisted_instagrams = []

    if req.emails:
        existing = (
            db.query(Blacklist.email)
            .filter(Blacklist.user_id == current_user.id, Blacklist.email.in_(req.emails))
            .all()
        )
        blacklisted_emails = [row[0] for row in existing if row[0]]

    if req.instagrams:
        existing = (
            db.query(Blacklist.instagram)
            .filter(Blacklist.user_id == current_user.id, Blacklist.instagram.in_(req.instagrams))
            .all()
        )
        blacklisted_instagrams = [row[0] for row in existing if row[0]]

    return BlacklistCheckResponse(
        blacklisted_emails=blacklisted_emails,
        blacklisted_instagrams=blacklisted_instagrams,
    )
