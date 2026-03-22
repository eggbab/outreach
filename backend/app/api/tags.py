from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Prospect, ProspectTag, Tag, User

router = APIRouter(prefix="/api/tags", tags=["tags"])


class TagCreate(BaseModel):
    name: str
    color: str = "#3B82F6"


class TagResponse(BaseModel):
    id: int
    name: str
    color: str

    model_config = {"from_attributes": True}


class TagAttach(BaseModel):
    prospect_id: int
    tag_id: int


@router.get("/", response_model=list[TagResponse])
def list_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Tag).filter(Tag.user_id == current_user.id).all()


@router.post("/", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    req: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = (
        db.query(Tag)
        .filter(Tag.user_id == current_user.id, Tag.name == req.name)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Tag already exists")
    tag = Tag(user_id=current_user.id, name=req.name, color=req.color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.put("/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: int,
    req: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == current_user.id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    tag.name = req.name
    tag.color = req.color
    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == current_user.id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    db.delete(tag)
    db.commit()


@router.post("/attach", status_code=status.HTTP_201_CREATED)
def attach_tag(
    req: TagAttach,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tag = db.query(Tag).filter(Tag.id == req.tag_id, Tag.user_id == current_user.id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    existing = (
        db.query(ProspectTag)
        .filter(ProspectTag.prospect_id == req.prospect_id, ProspectTag.tag_id == req.tag_id)
        .first()
    )
    if existing:
        return {"message": "Tag already attached"}

    pt = ProspectTag(prospect_id=req.prospect_id, tag_id=req.tag_id)
    db.add(pt)
    db.commit()
    return {"message": "Tag attached"}


@router.post("/detach", status_code=status.HTTP_200_OK)
def detach_tag(
    req: TagAttach,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pt = (
        db.query(ProspectTag)
        .filter(ProspectTag.prospect_id == req.prospect_id, ProspectTag.tag_id == req.tag_id)
        .first()
    )
    if pt:
        db.delete(pt)
        db.commit()
    return {"message": "Tag detached"}
