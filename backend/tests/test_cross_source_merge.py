"""교차 소스 병합 — 여러 채널에서 찾은 같은 업체를 하나의 완성된 데이터로."""
from app.services.collector.manager import merge_cross_source


class TestCrossSourceMerge:
    def test_same_phone_merges_and_fills_missing_fields(self):
        """카카오(전화만) + 네이버 검색(이메일만)이 같은 전화번호로 만나면 하나가 된다."""
        raw = [
            {"name": "커피한잔", "phone": "02-555-1234", "source": "kakao",
             "description": "카페 · 강남구"},
            {"name": "커피한잔 강남점", "phone": "025551234", "email": "hi@coffee.kr",
             "website": "https://coffee.kr", "source": "naver"},
        ]
        out = merge_cross_source(raw)
        assert len(out) == 1
        m = out[0]
        assert m["email"] == "hi@coffee.kr"          # 네이버가 보완
        assert m["phone"] == "02-555-1234"           # 먼저 온 카카오 형식 유지
        assert m["description"] == "카페 · 강남구"    # 카카오 요약 유지
        assert m["source"] == "kakao+naver"          # 출처 합산
        assert m["verified_count"] == 2              # 두 곳에서 교차 확인

    def test_same_website_domain_merges(self):
        raw = [
            {"name": "A", "website": "https://www.shop.co.kr/about", "email": "a@shop.co.kr", "source": "naver"},
            {"name": "A샵", "website": "http://shop.co.kr", "instagram": "a_shop", "source": "google"},
        ]
        out = merge_cross_source(raw)
        assert len(out) == 1
        assert out[0]["instagram"] == "a_shop"

    def test_different_businesses_stay_separate(self):
        raw = [
            {"name": "가게1", "phone": "02-111-1111", "source": "kakao"},
            {"name": "가게2", "phone": "02-222-2222", "source": "kakao"},
        ]
        assert len(merge_cross_source(raw)) == 2

    def test_chained_identity(self):
        """A=B(전화 일치), B=C(도메인 일치)면 셋 다 한 업체다."""
        raw = [
            {"name": "X", "phone": "02-333-4444", "source": "kakao"},
            {"name": "X", "phone": "0233344 44", "website": "https://x.kr", "source": "naver_map"},
            {"name": "X컴퍼니", "website": "https://www.x.kr", "email": "x@x.kr", "source": "google"},
        ]
        out = merge_cross_source(raw)
        assert len(out) == 1
        assert out[0]["email"] == "x@x.kr"
        assert out[0]["verified_count"] == 3

    def test_empty_input(self):
        assert merge_cross_source([]) == []
