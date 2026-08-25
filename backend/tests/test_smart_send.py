"""스마트 발송 시간 계산 테스트.

반환값은 naive-UTC. best_hour는 KST 벽시계로 해석하므로 UTC 시각은 KST-9.
예: KST 10시 = UTC 01시.
"""
from datetime import datetime, timezone

from app.models.models import GlobalProspect, IndustryBenchmark, Prospect
from app.services.smart_send import compute_smart_send_at, DEFAULT_HOUR

KST_TO_UTC = 9  # KST hour - 9 = UTC hour


class TestSmartSend:
    def test_default_hour_when_no_benchmark(self, db_session, project_id):
        # KST 기준 화요일 새벽 (UTC 월 22시 = KST 화 07시)
        base = datetime(2026, 9, 1, 7 - KST_TO_UTC + 24, tzinfo=timezone.utc) if False else datetime(2026, 8, 31, 22, 0, tzinfo=timezone.utc)
        when, reason = compute_smart_send_at(db_session, project_id, now=base)
        # KST 10시 = UTC 01시
        assert when.hour == (DEFAULT_HOUR - KST_TO_UTC) % 24
        assert "권장" in reason

    def test_past_hour_moves_to_next_day(self, db_session, project_id):
        # KST 화 15시 (UTC 화 06시) — KST 10시 지남 → 다음날
        base = datetime(2026, 9, 1, 6, 0, tzinfo=timezone.utc)
        when, _ = compute_smart_send_at(db_session, project_id, now=base)
        assert when.hour == (DEFAULT_HOUR - KST_TO_UTC) % 24  # UTC 01시
        assert when > base.replace(tzinfo=None)  # 미래 시각 (naive 비교)

    def test_weekend_skipped(self, db_session, project_id):
        # KST 금 15시 (UTC 금 06시) → 다음 KST 발송은 월요일이어야
        base = datetime(2026, 9, 4, 6, 0, tzinfo=timezone.utc)
        when, _ = compute_smart_send_at(db_session, project_id, now=base)
        # UTC 시각을 KST로 되돌려 요일 확인
        from datetime import timedelta
        kst = when + timedelta(hours=9)
        assert kst.weekday() == 0  # 월요일

    def test_uses_industry_benchmark(self, db_session, project_id):
        gp = GlobalProspect(company_name="A", email="a@corp.com", industry="외식업")
        db_session.add(gp)
        db_session.flush()
        db_session.add(Prospect(project_id=project_id, name="A", email="a@corp.com",
                                status="approved", global_prospect_id=gp.id))
        db_session.add(IndustryBenchmark(industry="외식업", best_send_hour=14, sample_size=100))
        db_session.commit()

        base = datetime(2026, 8, 31, 22, 0, tzinfo=timezone.utc)  # KST 화 07시
        when, reason = compute_smart_send_at(db_session, project_id, now=base)
        assert when.hour == (14 - KST_TO_UTC) % 24  # KST 14시 = UTC 05시
        assert "외식업" in reason

    def test_low_sample_benchmark_ignored(self, db_session, project_id):
        gp = GlobalProspect(company_name="B", email="b@corp.com", industry="뷰티")
        db_session.add(gp)
        db_session.flush()
        db_session.add(Prospect(project_id=project_id, name="B", email="b@corp.com",
                                status="approved", global_prospect_id=gp.id))
        db_session.add(IndustryBenchmark(industry="뷰티", best_send_hour=16, sample_size=10))
        db_session.commit()
        base = datetime(2026, 8, 31, 22, 0, tzinfo=timezone.utc)
        when, _ = compute_smart_send_at(db_session, project_id, now=base)
        assert when.hour == (DEFAULT_HOUR - KST_TO_UTC) % 24  # 기본값 KST 10시 = UTC 01시
