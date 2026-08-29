"""정부 등록부 수집기 — 로컬 미러 검색."""
import pytest

from app.models.models import FtcBusiness
from app.services.collector import ftc


@pytest.fixture
def mirror(db_session, monkeypatch):
    """테스트 DB를 수집기가 쓰도록 연결 + 표본 데이터."""
    import app.core.database as core_db
    monkeypatch.setattr(core_db, "SessionLocal", lambda: db_session)
    # 수집기가 세션을 닫아도 테스트 픽스처가 죽지 않게
    monkeypatch.setattr(db_session, "close", lambda: None)
    rows = [
        FtcBusiness(brno="1000000001", name="강남커피컴퍼니", email="a@ca.kr",
                    phone="02-1", address="서울 강남구 테헤란로 1",
                    product="원두, 커피용품", declared_date="20260101"),
        FtcBusiness(brno="1000000002", name="부산베이커리", email="b@bk.kr",
                    phone="051-1", address="부산 해운대구",
                    product="빵", declared_date="20250601"),
        FtcBusiness(brno="1000000003", name="커피나라", email=None,
                    phone="02-3", address="서울 마포구", product="커피",
                    declared_date="20240101"),
    ]
    db_session.add_all(rows)
    db_session.commit()
    return rows


class TestFtcMirrorSearch:
    def test_empty_mirror_skips_silently(self, db_session, monkeypatch):
        import app.core.database as core_db
        monkeypatch.setattr(core_db, "SessionLocal", lambda: db_session)
        monkeypatch.setattr(db_session, "close", lambda: None)
        assert ftc.search_ftc("카페") == []

    def test_multi_word_intersects_name_and_address(self, mirror):
        """'강남 커피' → 상호/주소/품목 어디든 두 단어 다 걸린 업체만."""
        out = ftc.search_ftc("강남 커피")
        assert [p["name"] for p in out] == ["강남커피컴퍼니"]
        p = out[0]
        assert p["email"] == "a@ca.kr"
        assert p["source"] == "ftc"
        assert "정부 등록 업체" in p["description"]

    def test_product_field_is_searched(self, mirror):
        names = {p["name"] for p in ftc.search_ftc("커피")}
        assert names == {"강남커피컴퍼니", "커피나라"}

    def test_strict_limits_to_business_name(self, mirror):
        out = ftc.search_ftc("강남", match_level="strict")
        assert [p["name"] for p in out] == ["강남커피컴퍼니"]  # 주소의 '강남구'는 제외

    def test_recent_first_and_max_results(self, mirror):
        out = ftc.search_ftc("커피", max_results=1)
        assert len(out) == 1
        assert out[0]["name"] == "강남커피컴퍼니"  # 신고일 최신 우선
