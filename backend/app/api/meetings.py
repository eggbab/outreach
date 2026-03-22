import secrets
from datetime import datetime, time, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Activity, Meeting, MeetingSlot, User

router = APIRouter(tags=["meetings"])

slot_router = APIRouter(prefix="/api/meeting-slots")
meeting_router = APIRouter(prefix="/api/meetings")
booking_router = APIRouter(prefix="/api/book")


# ── Schemas ──

class SlotCreate(BaseModel):
    day_of_week: int  # 0=Monday
    start_time: str  # "09:00"
    end_time: str  # "17:00"
    duration_minutes: int = 30
    is_active: bool = True


class SlotResponse(BaseModel):
    id: int
    day_of_week: int
    start_time: str
    end_time: str
    duration_minutes: int
    is_active: bool

    model_config = {"from_attributes": True}


class MeetingCreate(BaseModel):
    prospect_id: Optional[int] = None
    title: str
    scheduled_at: datetime
    duration_minutes: int = 30


class MeetingResponse(BaseModel):
    id: int
    booking_code: str
    title: str
    scheduled_at: datetime
    duration_minutes: int
    status: str
    booker_name: Optional[str] = None
    booker_email: Optional[str] = None
    prospect_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BookingRequest(BaseModel):
    booker_name: str
    booker_email: str
    scheduled_at: datetime
    title: str = "미팅 예약"


# ── Slots ──

@slot_router.get("/", response_model=list[SlotResponse])
def list_slots(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    slots = db.query(MeetingSlot).filter(MeetingSlot.user_id == current_user.id).order_by(MeetingSlot.day_of_week, MeetingSlot.start_time).all()
    return [
        SlotResponse(
            id=s.id,
            day_of_week=s.day_of_week,
            start_time=s.start_time.strftime("%H:%M"),
            end_time=s.end_time.strftime("%H:%M"),
            duration_minutes=s.duration_minutes,
            is_active=s.is_active,
        )
        for s in slots
    ]


@slot_router.post("/", response_model=SlotResponse, status_code=status.HTTP_201_CREATED)
def create_slot(
    req: SlotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start = time.fromisoformat(req.start_time)
    end = time.fromisoformat(req.end_time)
    slot = MeetingSlot(
        user_id=current_user.id,
        day_of_week=req.day_of_week,
        start_time=start,
        end_time=end,
        duration_minutes=req.duration_minutes,
        is_active=req.is_active,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return SlotResponse(
        id=slot.id, day_of_week=slot.day_of_week,
        start_time=slot.start_time.strftime("%H:%M"),
        end_time=slot.end_time.strftime("%H:%M"),
        duration_minutes=slot.duration_minutes, is_active=slot.is_active,
    )


@slot_router.delete("/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    slot = db.query(MeetingSlot).filter(MeetingSlot.id == slot_id, MeetingSlot.user_id == current_user.id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    db.delete(slot)
    db.commit()


# ── Meetings ──

@meeting_router.get("/", response_model=list[MeetingResponse])
def list_meetings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Meeting)
        .filter(Meeting.user_id == current_user.id)
        .order_by(Meeting.scheduled_at.desc())
        .all()
    )


@meeting_router.post("/", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
def create_meeting(
    req: MeetingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = Meeting(
        user_id=current_user.id,
        prospect_id=req.prospect_id,
        booking_code=secrets.token_urlsafe(12),
        title=req.title,
        scheduled_at=req.scheduled_at,
        duration_minutes=req.duration_minutes,
    )
    db.add(meeting)

    if req.prospect_id:
        activity = Activity(
            user_id=current_user.id,
            prospect_id=req.prospect_id,
            activity_type="meeting_booked",
            description=f"미팅 예약: {req.title}",
        )
        db.add(activity)

    db.commit()
    db.refresh(meeting)
    return meeting


@meeting_router.put("/{meeting_id}/cancel")
def cancel_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.user_id == current_user.id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    meeting.status = "cancelled"
    db.commit()
    return {"status": "cancelled"}


# ── Public booking ──

@booking_router.get("/{user_id}/slots")
def get_public_slots(
    user_id: int,
    db: Session = Depends(get_db),
):
    slots = (
        db.query(MeetingSlot)
        .filter(MeetingSlot.user_id == user_id, MeetingSlot.is_active == True)
        .order_by(MeetingSlot.day_of_week, MeetingSlot.start_time)
        .all()
    )
    return [
        {
            "day_of_week": s.day_of_week,
            "start_time": s.start_time.strftime("%H:%M"),
            "end_time": s.end_time.strftime("%H:%M"),
            "duration_minutes": s.duration_minutes,
        }
        for s in slots
    ]


@booking_router.post("/{user_id}", response_model=MeetingResponse)
def book_meeting(
    user_id: int,
    req: BookingRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    meeting = Meeting(
        user_id=user_id,
        booking_code=secrets.token_urlsafe(12),
        title=req.title,
        scheduled_at=req.scheduled_at,
        booker_name=req.booker_name,
        booker_email=req.booker_email,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting
