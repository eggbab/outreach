"""인스타 DM 파이프라인 계약 테스트 — 큐/결과 payload가 확장과 맞는지 고정.

이 계약이 깨지면 확장이 다시 조용히 발송 0건이 되므로, 필드명을 여기서 못박는다.
"""
from datetime import datetime, timezone

import pytest

from app.models.models import Blacklist, DmLog, GlobalUnsubscribe, Prospect, User, UserSettings
from app.services.dm_compose import render_dm


def _mk_prospect(db, project_id, **kw):
    p = Prospect(project_id=project_id, status="approved", **kw)
    db.add(p)
    db.flush()
    return p


# ──────────────────────────────────────
# 스핀택스 / 변형
# ──────────────────────────────────────

class TestDmCompose:
    def test_spintax_expands_and_varies(self):
        t = "{안녕하세요|반갑습니다|안녕하십니까} {company}님"
        a = render_dm(t, company_name="A", prospect_id=1)
        b = render_dm(t, company_name="A", prospect_id=2)
        assert "{" not in a and "|" not in a
        assert a.endswith("A님") and b.endswith("A님")

    def test_variable_substitution_all_forms(self):
        msg = render_dm("{company} {company_name} {name} @{username}",
                        company_name="터틀힙", username="turtlehip", prospect_id=1)
        assert "터틀힙 터틀힙 터틀힙 @turtlehip" in msg

    def test_auto_vary_adds_greeting_and_closing(self):
        msg = render_dm("서비스를 소개드립니다.", company_name="A", prospect_id=3)
        assert msg.startswith(("안녕", "반갑"))
        assert "A" in msg

    def test_deterministic_same_seed(self):
        t = "{a|b|c} 테스트"
        assert render_dm(t, prospect_id=7) == render_dm(t, prospect_id=7)


# ──────────────────────────────────────
# 큐 payload 계약
# ──────────────────────────────────────

class TestDmQueueContract:
    def test_queue_returns_extension_shape(self, client, auth_headers, project_id, db_session):
        _mk_prospect(db_session, project_id, name="성수카페", instagram="seongsu_cafe", email="a@corp.com")
        db_session.commit()

        res = client.get(f"/api/chrome/dm-queue?project_id={project_id}", headers=auth_headers)
        assert res.status_code == 200
        body = res.json()
        # 확장이 소비하는 정확한 필드 (instagram-dm.js가 읽는 이름)
        assert set(body.keys()) >= {
            "targets", "total", "daily_limit", "sent_today",
            "hourly_limit", "min_delay_seconds", "max_delay_seconds",
            "night_block", "max_consecutive_failures",
        }
        # 안전 정책 값이 합리적 범위
        assert body["hourly_limit"] >= 1
        assert body["min_delay_seconds"] >= 60      # DM 최소 간격 1분 이상
        assert body["night_block"] is True
        assert body["max_consecutive_failures"] >= 1
        t = body["targets"][0]
        assert set(t.keys()) >= {"prospect_id", "username", "instagram_pk", "message"}
        assert t["username"] == "seongsu_cafe"
        assert "성수카페" in t["message"]  # 개인화됨
        assert "{" not in t["message"]     # 스핀택스 전개됨

    def test_queue_normalizes_handle(self, client, auth_headers, project_id, db_session):
        _mk_prospect(db_session, project_id, name="A", instagram="https://instagram.com/MyShop/?hl=ko")
        db_session.commit()
        res = client.get(f"/api/chrome/dm-queue?project_id={project_id}", headers=auth_headers)
        assert res.json()["targets"][0]["username"] == "myshop"

    def test_queue_ownership_enforced(self, client, auth_headers, project_id, db_session):
        # 다른 유저의 프로젝트 id로 접근 → 404 (IDOR 차단)
        other = User(email="other@x.com", name="other", password_hash="x", credits=30)
        db_session.add(other)
        db_session.flush()
        from app.models.models import Project
        other_proj = Project(user_id=other.id, name="남의 프로젝트")
        db_session.add(other_proj)
        db_session.commit()
        res = client.get(f"/api/chrome/dm-queue?project_id={other_proj.id}", headers=auth_headers)
        assert res.status_code == 404

    def test_queue_skips_suppressed(self, client, auth_headers, project_id, db_session):
        _mk_prospect(db_session, project_id, name="차단될곳", instagram="blocked_biz", email="opt@corp.com")
        db_session.add(GlobalUnsubscribe(email="opt@corp.com"))
        db_session.commit()
        res = client.get(f"/api/chrome/dm-queue?project_id={project_id}", headers=auth_headers)
        assert all(t["username"] != "blocked_biz" for t in res.json()["targets"])

    def test_queue_respects_warmup_limit(self, client, auth_headers, project_id, db_session):
        # 새 계정(오늘 가입) → 워밍업 첫날 DM 한도 0 → 빈 큐
        for i in range(5):
            _mk_prospect(db_session, project_id, name=f"업체{i}", instagram=f"biz{i}")
        db_session.commit()
        res = client.get(f"/api/chrome/dm-queue?project_id={project_id}", headers=auth_headers)
        body = res.json()
        # 워밍업 첫날 한도(0)면 빈 큐, 아니면 한도 이하
        assert len(body["targets"]) <= body["daily_limit"]


# ──────────────────────────────────────
# 결과 보고 계약 + 크레딧 + PK 캐싱
# ──────────────────────────────────────

class TestDmResultContract:
    def test_result_records_and_charges(self, client, auth_headers, project_id, db_session):
        user = db_session.query(User).first()
        start = user.credits
        p = _mk_prospect(db_session, project_id, name="A", instagram="biz_a")
        db_session.commit()

        res = client.post("/api/chrome/dm-result", headers=auth_headers, json={
            "prospect_id": p.id, "status": "success",
            "message_body": "안녕하세요 A님", "instagram_pk": "17841400000000000",
        })
        assert res.status_code == 200
        db_session.refresh(user)
        db_session.refresh(p)
        assert user.credits == start - 3        # DM 3크레딧 차감
        assert p.status == "dm_sent"
        assert p.instagram_pk == "17841400000000000"  # PK 캐싱됨
        log = db_session.query(DmLog).filter(DmLog.prospect_id == p.id).first()
        assert log.message_body == "안녕하세요 A님"

    def test_no_credits_success_downgraded_to_failed(self, client, auth_headers, project_id, db_session):
        """크레딧 부족 시 확장이 success 보고해도 무과금 발송을 인정하지 않음."""
        user = db_session.query(User).first()
        user.credits = 1  # DM 1건(3크레딧) 부족
        p = _mk_prospect(db_session, project_id, name="A", instagram="biz_a")
        db_session.commit()
        res = client.post("/api/chrome/dm-result", headers=auth_headers, json={
            "prospect_id": p.id, "status": "success", "message_body": "안녕",
        })
        assert res.status_code == 200
        assert res.json()["status"] == "failed"  # success → failed로 강등
        db_session.refresh(user)
        db_session.refresh(p)
        assert user.credits == 1        # 차감 안 됨
        assert p.status != "dm_sent"    # 발송 미확정

    def test_failed_result_no_charge(self, client, auth_headers, project_id, db_session):
        user = db_session.query(User).first()
        start = user.credits
        p = _mk_prospect(db_session, project_id, name="A", instagram="biz_a")
        db_session.commit()
        res = client.post("/api/chrome/dm-result", headers=auth_headers, json={
            "prospect_id": p.id, "status": "failed", "error_message": "ACCOUNT_NOT_FOUND",
        })
        assert res.status_code == 200
        db_session.refresh(user)
        assert user.credits == start  # 실패는 무과금

    def test_permanent_failure_excluded_from_queue(self, client, auth_headers, project_id, db_session):
        """계정 없음(영구 실패)은 큐에서 제외 — 무한 재시도 방지."""
        p = _mk_prospect(db_session, project_id, name="삭제된계정", instagram="deleted_acc")
        db_session.flush()
        user = db_session.query(User).first()
        db_session.add(DmLog(prospect_id=p.id, user_id=user.id, status="failed",
                             error_message="ACCOUNT_NOT_FOUND"))
        db_session.commit()
        res = client.get(f"/api/chrome/dm-queue?project_id={project_id}", headers=auth_headers)
        assert all(t["username"] != "deleted_acc" for t in res.json()["targets"])

    def test_transient_failure_retried(self, client, auth_headers, project_id, db_session):
        """일시 실패(네트워크 등)는 큐에 다시 포함 — 재시도 가능."""
        p = _mk_prospect(db_session, project_id, name="일시오류", instagram="transient_biz")
        db_session.flush()
        user = db_session.query(User).first()
        db_session.add(DmLog(prospect_id=p.id, user_id=user.id, status="failed",
                             error_message="send_failed_500"))
        db_session.commit()
        res = client.get(f"/api/chrome/dm-queue?project_id={project_id}", headers=auth_headers)
        # 일시 실패는 daily_limit 여유가 있으면 재시도 대상
        usernames = [t["username"] for t in res.json()["targets"]]
        assert "transient_biz" in usernames or res.json()["daily_limit"] == 0

    def test_cached_pk_returned_in_queue(self, client, auth_headers, project_id, db_session):
        _mk_prospect(db_session, project_id, name="A", instagram="biz_a", instagram_pk="123456")
        db_session.commit()
        res = client.get(f"/api/chrome/dm-queue?project_id={project_id}", headers=auth_headers)
        # 캐시된 PK가 있으면 확장이 재조회 안 하도록 그대로 전달
        target = next(t for t in res.json()["targets"] if t["username"] == "biz_a")
        assert target["instagram_pk"] == "123456"
