"""정부 등록부(통신판매사업자) 수집기 — 외부 호출은 전부 모킹."""
import httpx
import pytest

from app.services.collector import ftc


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def _ftc_payload(items):
    return {"response": {"body": {"items": items}}}


@pytest.fixture
def api_key(monkeypatch):
    monkeypatch.setenv("DATA_GO_KR_API_KEY", "test-key")


class TestFtcCollector:
    def test_skips_silently_without_key(self, monkeypatch):
        monkeypatch.delenv("DATA_GO_KR_API_KEY", raising=False)
        assert ftc.search_ftc("카페") == []

    def test_parses_registry_rows(self, api_key, monkeypatch):
        rows = [{
            "bzmnNm": "커피컴퍼니", "brno": "123-45-67890",
            "telno": "02-555-0001", "email": "hello@coffee.kr",
            "domnNm": "coffee.kr", "rnAddr": "서울 강남구 테헤란로 1",
            "rprsvNm": "김대표", "operSttusCdNm": "정상영업",
        }]
        monkeypatch.setattr(httpx.Client, "get",
                            lambda self, url, params=None: FakeResponse(200, _ftc_payload(rows)))
        monkeypatch.setattr(ftc, "filter_closed_businesses", lambda nos, key: set())

        out = ftc.search_ftc("카페", max_results=10)
        assert len(out) == 1
        p = out[0]
        assert p["name"] == "커피컴퍼니"
        assert p["email"] == "hello@coffee.kr"
        assert p["phone"] == "02-555-0001"
        assert p["website"] == "http://coffee.kr"
        assert p["source"] == "ftc"
        assert "김대표" in p["description"] and "테헤란로" in p["description"]

    def test_drops_rows_without_contact(self, api_key, monkeypatch):
        rows = [{"bzmnNm": "연락처없는곳", "brno": "111-11-11111"}]
        monkeypatch.setattr(httpx.Client, "get",
                            lambda self, url, params=None: FakeResponse(200, _ftc_payload(rows)))
        monkeypatch.setattr(ftc, "filter_closed_businesses", lambda nos, key: set())
        assert ftc.search_ftc("카페") == []

    def test_drops_closed_status_from_registry(self, api_key, monkeypatch):
        rows = [{"bzmnNm": "문닫은곳", "brno": "222-22-22222",
                 "telno": "02-1", "operSttusCdNm": "폐업"}]
        monkeypatch.setattr(httpx.Client, "get",
                            lambda self, url, params=None: FakeResponse(200, _ftc_payload(rows)))
        monkeypatch.setattr(ftc, "filter_closed_businesses", lambda nos, key: set())
        assert ftc.search_ftc("카페") == []

    def test_nts_filter_removes_closed(self, api_key, monkeypatch):
        rows = [
            {"bzmnNm": "살아있는곳", "brno": "100-00-00001", "telno": "02-1"},
            {"bzmnNm": "폐업한곳", "brno": "100-00-00002", "telno": "02-2"},
        ]
        monkeypatch.setattr(httpx.Client, "get",
                            lambda self, url, params=None: FakeResponse(200, _ftc_payload(rows)))
        monkeypatch.setattr(ftc, "filter_closed_businesses",
                            lambda nos, key: {"1000000002"})
        out = ftc.search_ftc("가게")
        assert [p["name"] for p in out] == ["살아있는곳"]

    def test_survives_non_json_response(self, api_key, monkeypatch):
        """키 미승인 시 XML 에러가 오는데, 죽지 않고 빈 결과여야 한다."""
        monkeypatch.setattr(httpx.Client, "get",
                            lambda self, url, params=None: FakeResponse(200, None, text="<xml>err</xml>"))
        monkeypatch.setattr(ftc, "filter_closed_businesses", lambda nos, key: set())
        assert ftc.search_ftc("카페") == []

    def test_nts_batch_parses_status_codes(self, api_key, monkeypatch):
        calls = []
        def fake_post(self, url, params=None, json=None):
            calls.append(json["b_no"])
            return FakeResponse(200, {"data": [
                {"b_no": json["b_no"][0], "b_stt_cd": "03"},   # 폐업
                *[{"b_no": n, "b_stt_cd": "01"} for n in json["b_no"][1:]],
            ]})
        monkeypatch.setattr(httpx.Client, "post", fake_post)
        closed = ftc.filter_closed_businesses(["123-45-67890", "999-99-99999"], "k")
        assert closed == {"1234567890"}
        assert calls == [["1234567890", "9999999999"]]
