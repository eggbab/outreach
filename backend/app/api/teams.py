from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Team, TeamMember, TeamProject, User

router = APIRouter(prefix="/api/teams", tags=["teams"])


class TeamCreate(BaseModel):
    name: str


class TeamResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    created_at: datetime
    member_count: int = 0

    model_config = {"from_attributes": True}


class MemberResponse(BaseModel):
    id: int
    user_id: int
    email: str
    name: str
    role: str

    model_config = {"from_attributes": True}


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "member"


class RoleChangeRequest(BaseModel):
    role: str


class ShareProjectRequest(BaseModel):
    project_id: int


@router.get("/", response_model=list[TeamResponse])
def list_teams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Teams where user is owner or member
    member_team_ids = (
        db.query(TeamMember.team_id)
        .filter(TeamMember.user_id == current_user.id)
        .subquery()
    )
    teams = (
        db.query(Team)
        .filter((Team.owner_id == current_user.id) | (Team.id.in_(member_team_ids)))
        .all()
    )
    results = []
    for team in teams:
        count = db.query(TeamMember).filter(TeamMember.team_id == team.id).count()
        results.append(TeamResponse(
            id=team.id, name=team.name, owner_id=team.owner_id,
            created_at=team.created_at, member_count=count,
        ))
    return results


@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    req: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = Team(name=req.name, owner_id=current_user.id)
    db.add(team)
    db.flush()
    # Owner is automatically admin
    member = TeamMember(team_id=team.id, user_id=current_user.id, role="admin")
    db.add(member)
    db.commit()
    db.refresh(team)
    return TeamResponse(id=team.id, name=team.name, owner_id=team.owner_id, created_at=team.created_at, member_count=1)


@router.get("/{team_id}/members", response_model=list[MemberResponse])
def list_members(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_team_access(team_id, current_user.id, db)
    members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
    results = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        if user:
            results.append(MemberResponse(
                id=m.id, user_id=m.user_id, email=user.email,
                name=user.name, role=m.role,
            ))
    return results


@router.post("/{team_id}/invite")
def invite_member(
    team_id: int,
    req: InviteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_team_admin(team_id, current_user.id, db)
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found with this email")

    existing = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member")

    member = TeamMember(team_id=team_id, user_id=user.id, role=req.role)
    db.add(member)
    db.commit()
    return {"message": f"{req.email} invited"}


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    team_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_team_admin(team_id, current_user.id, db)
    team = db.query(Team).filter(Team.id == team_id).first()
    if team.owner_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove team owner")
    member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(member)
    db.commit()


@router.put("/{team_id}/members/{user_id}/role")
def change_role(
    team_id: int,
    user_id: int,
    req: RoleChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_team_admin(team_id, current_user.id, db)
    if req.role not in ("admin", "member"):
        raise HTTPException(status_code=400, detail="Invalid role")
    member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    member.role = req.role
    db.commit()
    return {"role": member.role}


@router.post("/{team_id}/projects")
def share_project(
    team_id: int,
    req: ShareProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_team_admin(team_id, current_user.id, db)
    existing = (
        db.query(TeamProject)
        .filter(TeamProject.team_id == team_id, TeamProject.project_id == req.project_id)
        .first()
    )
    if existing:
        return {"message": "Project already shared"}
    tp = TeamProject(team_id=team_id, project_id=req.project_id)
    db.add(tp)
    db.commit()
    return {"message": "Project shared"}


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = db.query(Team).filter(Team.id == team_id, Team.owner_id == current_user.id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found or not owner")
    db.delete(team)
    db.commit()


def _verify_team_access(team_id: int, user_id: int, db: Session):
    member = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a team member")


def _verify_team_admin(team_id: int, user_id: int, db: Session):
    member = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id).first()
    if not member or member.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
