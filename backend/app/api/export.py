import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Prospect, Project, User

router = APIRouter(prefix="/api/projects/{project_id}/export", tags=["export"])


@router.get("/prospects")
def export_prospects_csv(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    prospects = (
        db.query(Prospect)
        .filter(Prospect.project_id == project_id)
        .order_by(Prospect.collected_at.desc())
        .all()
    )

    output = io.StringIO()
    # BOM for Excel Korean support
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow(["업체명", "이메일", "전화번호", "인스타그램", "웹사이트", "소스", "카테고리", "상태", "스코어", "수집일"])

    for p in prospects:
        writer.writerow([
            p.name or "",
            p.email or "",
            p.phone or "",
            p.instagram or "",
            p.website or "",
            p.source or "",
            p.category or "",
            p.status,
            p.score,
            p.collected_at.strftime("%Y-%m-%d %H:%M") if p.collected_at else "",
        ])

    output.seek(0)
    filename = f"{project.name}_prospects.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
