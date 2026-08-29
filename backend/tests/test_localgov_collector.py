"""지자체 인허가 수집기 — 외부 호출 모킹."""
import httpx
import pytest

from app.services.collector import localgov


class FakeResponse:
    def __init__(self, payload):
        self.status_code = 200
        self._p = payload
    def json(self):
        return self._p


def _payload(rows):
    return {"result": {"body": {"rows": [{"row": rows}]}}}


@pytest.fixture
def api_key(monkeypatch):
    monkeypatch.setenv("LOCALDATA_API_KEY", "k")


class TestLocalgov:
    def test_skips_without_key(self, monkeypatch):
        monkeypatch.delenv("LOCALDATA_API_KEY", raising=False)
        assert localgov.search_localgov("서울 카페") == []

    def test_skips_unmapped_keyword(self, api_key):
        assert localgov.search_localgov("반도체 장비") == []

    def test_parses_rows_and_filters_region(self, api_key, monkeypatch):
        rows = [
            {"bplcNm": "강남카페", "rdnWhlAddr": "서울특별시 강남구 테헤란로 1",
             "siteTel": "02-111-2222", "uptaeNm": "커피숍"},
            {"bplcNm": "부산카페", "rdnWhlAddr": "부산광역시 해운대구",
             "siteTel": "051-333-4444", "uptaeNm": "커피숍"},
            {"bplcNm": "전화없는집", "rdnWhlAddr": "서울시 어딘가", "siteTel": ""},
        ]
        calls = {}
        def fake_get(self, url, params=None):
            calls.update(params)
            # 2페이지째는 빈 결과로 종료
            return FakeResponse(_payload(rows if params["pageIndex"] == 1 else []))
        monkeypatch.setattr(httpx.Client, "get", fake_get)

        out = localgov.search_localgov("서울 카페", max_results=10)
        assert [p["name"] for p in out] == ["강남카페"]   # 서울만 + 전화 있는 것만
        p = out[0]
        assert p["phone"] == "02-111-2222"
        assert p["source"] == "localgov"
        assert "지자체 인허가 업소" in p["description"]
        assert calls["opnSvcId"] == "07_24_05_P"          # 카페 → 휴게음식점
        assert calls["state"] == "01"                      # 영업중만

    def test_connection_failure_returns_empty(self, api_key, monkeypatch):
        def boom(self, url, params=None):
            raise httpx.ConnectError("refused")
        monkeypatch.setattr(httpx.Client, "get", boom)
        assert localgov.search_localgov("서울 식당") == []
