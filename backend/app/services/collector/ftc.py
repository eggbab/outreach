"""정부 등록부(통신판매사업자) 수집기 — 로컬 미러에서 검색.

전자상거래법상 통신판매업자는 상호·대표자·전화·이메일을 신고해야 하고
공정위가 공개한다. 즉 여기서 나오는 이메일·전화는 '정부에 신고된 공개
정보'라 수집 리스크가 없다.

정부 API가 상호 검색을 지원하지 않아(실호출로 확인 — 사업자번호 단건과
전체 목록뿐), services/ftc_sync.py 가 등록부를 로컬 DB로 미러링해두고
여기서는 그 미러를 상호·주소·취급품목 LIKE로 검색한다.

미러가 비어 있으면(키 미설정 또는 첫 동기화 전) 조용히 스킵.
"""
import logging

from sqlalchemy import or_

logger = logging.getLogger(__name__)


def search_ftc(keyword: str, max_results: int = 20, match_level: str = "medium") -> list[dict]:
    from app.core.database import SessionLocal
    from app.models.models import FtcBusiness

    db = SessionLocal()
    try:
        if db.query(FtcBusiness.id).first() is None:
            logger.info("[ftc] 등록부 미러 비어 있음 — 건너뜀 (DATA_GO_KR_API_KEY 설정 후 자동 적재)")
            return []

        # "강남 카페" → 단어별로 상호/주소/품목에 걸어본다.
        # 모든 단어가 (어느 필드든) 걸린 업체 = 교집합. strict면 상호에 한정.
        words = [w for w in keyword.split() if len(w) >= 2] or [keyword]
        q = db.query(FtcBusiness)
        for w in words:
            like = f"%{w}%"
            if match_level == "strict":
                q = q.filter(FtcBusiness.name.ilike(like))
            else:
                q = q.filter(or_(
                    FtcBusiness.name.ilike(like),
                    FtcBusiness.address.ilike(like),
                    FtcBusiness.product.ilike(like),
                ))

        rows = (
            q.order_by(FtcBusiness.declared_date.desc())  # 최근 신고 = 살아있을 확률↑
            .limit(max_results)
            .all()
        )

        prospects = []
        for b in rows:
            desc_bits = [x for x in (b.product, b.address, "정부 등록 업체(통신판매 신고)") if x]
            prospects.append({
                "name": b.name,
                "email": b.email,
                "phone": b.phone,
                "instagram": None,
                "website": b.website,
                "source": "ftc",
                "category": keyword,
                "description": " · ".join(desc_bits) or None,
                "biz_no": b.brno,
            })
        logger.info(f"[ftc] '{keyword}' → 미러에서 {len(prospects)}건")
        return prospects
    except Exception as e:
        logger.error(f"[ftc] 미러 검색 실패 '{keyword}': {e}")
        return []
    finally:
        db.close()
