"""스마트 발송 시간 — 업종 벤치마크의 최적 발송 시각에 자동 예약.

발송 시 smart_send=true면 프로젝트 잠재고객의 주 업종을 파악하고,
그 업종의 best_send_hour(IndustryBenchmark, 실데이터 집계)에 예약한다.
벤치마크 데이터가 부족하면 B2B 이메일 최적 기본값(화·수·목 오전 10시)을 쓴다.
야간(21~08시)은 피한다(정보통신망법 + 열람률).
"""
from datetime import datetime, timedelta, timezone

DEFAULT_HOUR = 10          # 오전 10시 (B2B 이메일 최적)
NIGHT_START, NIGHT_END = 21, 8  # 야간 회피


def _dominant_industry(db, project_id: int) -> str | None:
    """프로젝트 잠재고객의 가장 흔한 업종."""
    from sqlalchemy import func
    from app.models.models import GlobalProspect, Prospect

    row = (
        db.query(GlobalProspect.industry, func.count(Prospect.id).label("c"))
        .join(Prospect, Prospect.global_prospect_id == GlobalProspect.id)
        .filter(Prospect.project_id == project_id, GlobalProspect.industry.isnot(None))
        .group_by(GlobalProspect.industry)
        .order_by(func.count(Prospect.id).desc())
        .first()
    )
    return row[0] if row else None


def _best_hour_for(db, project_id: int) -> tuple[int, str]:
    """(발송 시각, 근거 설명) 반환."""
    from app.models.models import IndustryBenchmark

    industry = _dominant_industry(db, project_id)
    if industry:
        b = db.query(IndustryBenchmark).filter(IndustryBenchmark.industry == industry).first()
        if b and b.best_send_hour is not None and (b.sample_size or 0) >= 50:
            h = int(b.best_send_hour)
            if NIGHT_END <= h < NIGHT_START:
                return h, f"'{industry}' 업종 최적 시각({h}시, 실데이터 {b.sample_size}건 기준)"
    return DEFAULT_HOUR, f"B2B 이메일 권장 시각(오전 {DEFAULT_HOUR}시)"


KST_OFFSET = timedelta(hours=9)  # 한국 표준시 = UTC+9


def compute_smart_send_at(db, project_id: int, *, now: datetime | None = None) -> tuple[datetime, str]:
    """다음 최적 발송 시각(naive-UTC)과 근거를 계산.

    best_hour는 한국(KST) 벽시계 시각으로 해석한다. 계산은 KST로 하고,
    스케줄러(process_scheduled_emails)가 naive-UTC로 비교하므로 최종 반환은 UTC로 변환.
    주말은 피하고(월~금), KST 기준으로 오늘 그 시각이 지났으면 다음 영업일로.
    """
    now_utc = now or datetime.now(timezone.utc)
    if now_utc.tzinfo is not None:
        now_utc = now_utc.replace(tzinfo=None)
    now_kst = now_utc + KST_OFFSET

    hour, reason = _best_hour_for(db, project_id)

    target_kst = now_kst.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target_kst <= now_kst:
        target_kst = target_kst + timedelta(days=1)
    while target_kst.weekday() >= 5:  # 5=토, 6=일
        target_kst = target_kst + timedelta(days=1)

    # KST → UTC(naive)로 변환해 저장 (스케줄러 비교 기준)
    target_utc = target_kst - KST_OFFSET
    return target_utc, reason
