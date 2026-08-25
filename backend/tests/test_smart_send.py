"""스마트 발송 시간 계산 테스트."""
from datetime import datetime, timezone

from app.models.models import GlobalProspect, IndustryBenchmark, Prospect
from app.services.smart_send import compute_smart_send_at, DEFAULT_HOUR


class TestSmartSend:
    def test_default_hour_when_no_benchmark(self, db_session, project_id):
        # 벤치마크 없음 → 기본 오전 10시
        base = datetime(2026, 9, 1, 7, 0, tzinfo=timezone.utc)  # 화요일 07시
        when, reason = compute_smart_send_at(db_session, project_id, now=base)
        assert when.hour == DEFAULT_HOUR
        assert when.date() == base.date()  # 오늘 10시 (아직 안 지남)
        assert "권장" in reason

    def test_past_hour_moves_to_next_day(self, db_session, project_id):
        base = datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc)  # 화 15시 (10시 지남)
        when, _ = compute_smart_send_at(db_session, project_id, now=base)
        assert when.hour == DEFAULT_HOUR
        assert when.day == 2  # 다음날 수요일

    def test_weekend_skipped(self, db_session, project_id):
        base = datetime(2026, 9, 4, 15, 0, tzinfo=timezone.utc)  # 금 15시 → 다음날 토
        when, _ = compute_smart_send_at(db_session, project_id, now=base)
        assert when.weekday() < 5  # 주말 아님 (월요일로)
        assert when.weekday() == 0  # 월요일

    def test_uses_industry_benchmark(self, db_session, project_id):
        # 업종 벤치마크가 충분(sample>=50)하면 그 시각 사용
        gp = GlobalProspect(company_name="A", email="a@corp.com", industry="외식업")
        db_session.add(gp)
        db_session.flush()
        db_session.add(Prospect(project_id=project_id, name="A", email="a@corp.com",
                                status="approved", global_prospect_id=gp.id))
        db_session.add(IndustryBenchmark(industry="외식업", best_send_hour=14, sample_size=100))
        db_session.commit()

        base = datetime(2026, 9, 1, 7, 0, tzinfo=timezone.utc)  # 화 07시
        when, reason = compute_smart_send_at(db_session, project_id, now=base)
        assert when.hour == 14
        assert "외식업" in reason

    def test_low_sample_benchmark_ignored(self, db_session, project_id):
        gp = GlobalProspect(company_name="B", email="b@corp.com", industry="뷰티")
        db_session.add(gp)
        db_session.flush()
        db_session.add(Prospect(project_id=project_id, name="B", email="b@corp.com",
                                status="approved", global_prospect_id=gp.id))
        db_session.add(IndustryBenchmark(industry="뷰티", best_send_hour=16, sample_size=10))  # 표본 부족
        db_session.commit()
        base = datetime(2026, 9, 1, 7, 0, tzinfo=timezone.utc)
        when, _ = compute_smart_send_at(db_session, project_id, now=base)
        assert when.hour == DEFAULT_HOUR  # 기본값으로 폴백
