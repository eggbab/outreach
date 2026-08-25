"""크레딧 원자성 테스트 — 동시 차감 시 lost update/음수 방지."""
from app.core.plans import add_credits, deduct_credits
from app.models.models import CreditTransaction, User


def _mk_user(db, credits=10):
    u = User(email="c@x.com", name="c", password_hash="x", credits=credits)
    db.add(u)
    db.flush()
    return u


class TestCreditAtomicity:
    def test_deduct_reduces_and_records(self, db_session):
        u = _mk_user(db_session, 10)
        bal = deduct_credits(db_session, u.id, 3, "발송")
        assert bal == 7
        db_session.refresh(u)
        assert u.credits == 7
        tx = db_session.query(CreditTransaction).filter_by(user_id=u.id).first()
        assert tx.amount == -3 and tx.balance_after == 7

    def test_deduct_rejects_insufficient(self, db_session):
        u = _mk_user(db_session, 2)
        assert deduct_credits(db_session, u.id, 5, "발송") is None
        db_session.refresh(u)
        assert u.credits == 2  # 변화 없음
        assert db_session.query(CreditTransaction).filter_by(user_id=u.id).count() == 0

    def test_deduct_exact_balance(self, db_session):
        u = _mk_user(db_session, 6)
        assert deduct_credits(db_session, u.id, 6, "발송") == 0
        db_session.refresh(u)
        assert u.credits == 0

    def test_sequential_deducts_never_go_negative(self, db_session):
        # 잔액 5에서 2씩 3번 → 마지막은 거부, 잔액 1
        u = _mk_user(db_session, 5)
        assert deduct_credits(db_session, u.id, 2, "1") == 3
        assert deduct_credits(db_session, u.id, 2, "2") == 1
        assert deduct_credits(db_session, u.id, 2, "3") is None  # 부족
        db_session.refresh(u)
        assert u.credits == 1

    def test_add_credits_atomic(self, db_session):
        u = _mk_user(db_session, 10)
        assert add_credits(db_session, u.id, 100, "충전") == 110
        db_session.refresh(u)
        assert u.credits == 110

    def test_deduct_zero_or_negative_noop(self, db_session):
        u = _mk_user(db_session, 10)
        assert deduct_credits(db_session, u.id, 0, "x") is None
        assert deduct_credits(db_session, u.id, -5, "x") is None
        db_session.refresh(u)
        assert u.credits == 10
