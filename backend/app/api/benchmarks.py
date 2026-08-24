from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import IndustryBenchmark

router = APIRouter(prefix="/api/benchmarks", tags=["benchmarks"])


class BenchmarkSummary(BaseModel):
    industry: str
    avg_open_rate: float = 0.0
    avg_click_rate: float = 0.0
    total_sent: int = 0
    sample_size: int = 0

    model_config = {"from_attributes": True}


class BenchmarkDetail(BaseModel):
    industry: str
    total_sent: int = 0
    total_opened: int = 0
    total_clicked: int = 0
    avg_open_rate: float = 0.0
    avg_click_rate: float = 0.0
    best_send_hour: int | None = None
    best_send_day: int | None = None
    sample_size: int = 0
    updated_at: str | None = None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[BenchmarkSummary])
def list_benchmarks(db: Session = Depends(get_db)):
    benchmarks = (
        db.query(IndustryBenchmark)
        .order_by(IndustryBenchmark.total_sent.desc())
        .all()
    )
    return [
        BenchmarkSummary(
            industry=b.industry,
            avg_open_rate=b.avg_open_rate,
            avg_click_rate=b.avg_click_rate,
            total_sent=b.total_sent,
            sample_size=b.sample_size,
        )
        for b in benchmarks
    ]


@router.get("/{industry}", response_model=BenchmarkDetail)
def get_benchmark(industry: str, db: Session = Depends(get_db)):
    b = db.query(IndustryBenchmark).filter(IndustryBenchmark.industry == industry).first()
    if not b:
        raise HTTPException(status_code=404, detail="해당 업종의 벤치마크 데이터가 없습니다")
    return BenchmarkDetail(
        industry=b.industry,
        total_sent=b.total_sent,
        total_opened=b.total_opened,
        total_clicked=b.total_clicked,
        avg_open_rate=b.avg_open_rate,
        avg_click_rate=b.avg_click_rate,
        best_send_hour=b.best_send_hour,
        best_send_day=b.best_send_day,
        sample_size=b.sample_size,
        updated_at=b.updated_at.isoformat() if b.updated_at else None,
    )
