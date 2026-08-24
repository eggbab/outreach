import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.plans import CREDIT_COSTS, check_credits, deduct_credits
from app.models.models import (
    Blacklist, CollectionJob, GlobalProspect, GlobalProspectContribution,
    Keyword, Prospect,
)
from app.services.collector.google import search_google
from app.services.collector.naver import search_naver, search_naver_map, search_naver_shopping

logger = logging.getLogger(__name__)

# Map source types to their collector functions.
# 인스타그램 ID는 별도 수집 안 함 — 네이버/구글에서 사이트 방문 시 인스타 링크 자동 추출됨.
SOURCE_COLLECTORS = {
    "naver": [search_naver, search_naver_shopping, search_naver_map],
    "google": [search_google],
    # Legacy individual sources (backward compat)
    "naver_shopping": [search_naver_shopping],
    "naver_map": [search_naver_map],
}

# Industry classification mapping
INDUSTRY_KEYWORDS = {
    "외식업": ["카페", "커피", "식당", "레스토랑", "음식", "베이커리", "빵", "치킨", "피자", "분식", "한식", "중식", "일식"],
    "인테리어": ["인테리어", "리모델링", "시공", "건축", "설계"],
    "법률": ["변호사", "법무", "법률", "로펌"],
    "의료": ["병원", "의원", "치과", "한의원", "약국", "의료"],
    "교육": ["학원", "과외", "교육", "학습", "코딩", "영어"],
    "부동산": ["부동산", "공인중개", "매매", "임대"],
    "뷰티": ["미용", "헤어", "네일", "피부", "에스테틱", "뷰티"],
    "헬스": ["헬스", "피트니스", "요가", "필라테스", "운동", "체육관"],
    "IT": ["소프트웨어", "개발", "IT", "웹", "앱", "프로그래밍", "테크"],
    "쇼핑몰": ["쇼핑몰", "온라인몰", "스토어", "판매"],
    "제조": ["제조", "공장", "생산", "가공"],
    "마케팅": ["마케팅", "광고", "홍보", "PR", "브랜딩"],
    "물류": ["물류", "배송", "운송", "택배"],
    "금융": ["보험", "금융", "증권", "투자", "은행"],
    "반려동물": ["펫", "애견", "동물병원", "반려"],
    "자동차": ["자동차", "카센터", "정비", "세차"],
    "여행": ["여행", "투어", "관광", "호텔", "숙박", "펜션"],
    "사진/영상": ["사진", "스튜디오", "촬영", "영상", "웨딩"],
    "농업": ["농장", "농업", "농산물", "과수원"],
    "기타서비스": ["청소", "세탁", "이사", "수리", "용역"],
}


def _classify_industry(category: str | None) -> str | None:
    if not category:
        return None
    cat_lower = category.lower()
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        for kw in keywords:
            if kw in cat_lower:
                return industry
    return None


class CollectionManager:
    """Orchestrates prospect collection across all configured sources."""

    def __init__(self, db: Session):
        self.db = db

    # All sources to try, in order of priority
    ALL_SOURCES = ["naver", "google", "naver_shopping", "naver_map"]

    def run_collection(self, project_id: int, user_id: int, max_results: int = 20, match_level: str = "medium") -> None:
        keywords = (
            self.db.query(Keyword)
            .filter(Keyword.project_id == project_id)
            .all()
        )

        # One task per keyword — each task tries all sources until max_results reached
        tasks = [(kw.id, kw.keyword, max_results) for kw in keywords]

        # Create or update job record
        job = (
            self.db.query(CollectionJob)
            .filter(CollectionJob.project_id == project_id, CollectionJob.user_id == user_id)
            .order_by(CollectionJob.started_at.desc())
            .first()
        )
        if not job or job.status != "running":
            job = CollectionJob(
                project_id=project_id,
                user_id=user_id,
                status="running",
                total_tasks=len(tasks),
                processed_tasks=0,
                prospects_found=0,
            )
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)

        if not tasks:
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            return

        total_prospects_found = 0

        for i, (keyword_id, keyword_text, max_results) in enumerate(tasks):
            job.processed_tasks = i
            job.current_task = keyword_text
            job.prospects_found = total_prospects_found
            self.db.commit()

            try:
                # Try all sources until we have enough results
                raw_prospects = []
                for source_key, collector_fns in SOURCE_COLLECTORS.items():
                    remaining = max_results - len(raw_prospects)
                    if remaining <= 0:
                        break
                    for fn in collector_fns:
                        remaining = max_results - len(raw_prospects)
                        if remaining <= 0:
                            break
                        try:
                            job.current_task = f"{keyword_text} ({source_key})"
                            self.db.commit()
                            raw_prospects.extend(fn(keyword_text, max_results=remaining, match_level=match_level))
                        except Exception as e:
                            logger.warning(f"Source {source_key} failed for '{keyword_text}': {e}")
                            continue
                saved = self._save_prospects(project_id, raw_prospects, user_id, keyword_id)
                total_prospects_found += saved

            except Exception as e:
                logger.error(f"Error collecting '{keyword_text}': {e}")
                continue

        job.status = "completed"
        job.processed_tasks = len(tasks)
        job.prospects_found = total_prospects_found
        job.current_task = None
        job.completed_at = datetime.now(timezone.utc)
        self.db.commit()

    def _save_prospects(self, project_id: int, raw_prospects: list[dict], user_id: int, keyword_id: int) -> int:
        """Save prospects to DB, skipping duplicates. Returns count of newly saved.
        매 건 저장 성공 시 1 크레딧 차감. 잔액 부족 시 중단."""
        saved_count = 0

        for data in raw_prospects:
            # 이메일 OR 인스타 핸들 OR 전화번호 중 하나라도 있어야 의미있는 prospect
            if not (data.get("email") or data.get("instagram") or data.get("phone")):
                continue

            # 크레딧 체크 — 부족하면 중단
            if not check_credits(self.db, user_id, "prospect", 1)["allowed"]:
                logger.warning(f"User {user_id} 크레딧 부족 — 수집 중단 ({saved_count}건 저장)")
                break

            existing = None
            if data.get("email"):
                existing = (
                    self.db.query(Prospect)
                    .filter(Prospect.project_id == project_id, Prospect.email == data["email"])
                    .first()
                )
            if not existing and data.get("website"):
                existing = (
                    self.db.query(Prospect)
                    .filter(Prospect.project_id == project_id, Prospect.website == data["website"])
                    .first()
                )
            if not existing and data.get("instagram"):
                existing = (
                    self.db.query(Prospect)
                    .filter(Prospect.project_id == project_id, Prospect.instagram == data["instagram"])
                    .first()
                )

            if existing:
                if data.get("email") and not existing.email:
                    existing.email = data["email"]
                if data.get("phone") and not existing.phone:
                    existing.phone = data["phone"]
                if data.get("instagram") and not existing.instagram:
                    existing.instagram = data["instagram"]
                continue

            # Check blacklist
            is_blacklisted = False
            if data.get("email"):
                if self.db.query(Blacklist).filter(Blacklist.user_id == user_id, Blacklist.email == data["email"]).first():
                    is_blacklisted = True
            if not is_blacklisted and data.get("instagram"):
                if self.db.query(Blacklist).filter(Blacklist.user_id == user_id, Blacklist.instagram == data["instagram"]).first():
                    is_blacklisted = True
            if is_blacklisted:
                continue

            prospect = Prospect(
                project_id=project_id,
                name=data.get("name"),
                email=data.get("email"),
                phone=data.get("phone"),
                instagram=data.get("instagram"),
                website=data.get("website"),
                source=data.get("source"),
                category=data.get("category"),
                keyword_id=keyword_id,
                status="collected",
            )
            self.db.add(prospect)
            self.db.flush()
            # 초기 스코어 — 보유 연락처 기반 (열람/클릭 시 tracking에서 재계산)
            from app.services.scoring import calculate_score
            prospect.score = calculate_score(self.db, prospect)
            saved_count += 1

            # 크레딧 차감 (수집 1건 = 1 크레딧)
            deduct_credits(self.db, user_id, CREDIT_COSTS["prospect"], f"잠재고객 수집: {data.get('email','')}")

            # Upsert to global prospect pool
            self._upsert_global_prospect(prospect, user_id)

        self.db.commit()
        return saved_count

    def _upsert_global_prospect(self, prospect: Prospect, user_id: int) -> None:
        """Create or update a GlobalProspect and link it to the Prospect."""
        gp = None

        # Look up by email first, then website, then instagram
        if prospect.email:
            gp = self.db.query(GlobalProspect).filter(GlobalProspect.email == prospect.email).first()
        if not gp and prospect.website:
            gp = self.db.query(GlobalProspect).filter(GlobalProspect.website == prospect.website).first()
        if not gp and prospect.instagram:
            gp = self.db.query(GlobalProspect).filter(GlobalProspect.instagram == prospect.instagram).first()

        industry = _classify_industry(prospect.category)

        if gp:
            gp.times_collected += 1
            # Merge empty fields
            if prospect.email and not gp.email:
                gp.email = prospect.email
            if prospect.phone and not gp.phone:
                gp.phone = prospect.phone
            if prospect.instagram and not gp.instagram:
                gp.instagram = prospect.instagram
            if prospect.website and not gp.website:
                gp.website = prospect.website
            if prospect.name and not gp.company_name:
                gp.company_name = prospect.name
            if prospect.category and not gp.category:
                gp.category = prospect.category
            if industry and not gp.industry:
                gp.industry = industry
        else:
            gp = GlobalProspect(
                company_name=prospect.name,
                email=prospect.email,
                phone=prospect.phone,
                instagram=prospect.instagram,
                website=prospect.website,
                source=prospect.source,
                category=prospect.category,
                industry=industry,
                times_collected=1,
                # 실사이트에서 추출된 이메일 = 약한 실존 증거 (발송/열람/답장 시 상향)
                email_validity_score=0.3 if prospect.email else 0.0,
            )
            self.db.add(gp)
            self.db.flush()

        # Link prospect to global prospect
        prospect.global_prospect_id = gp.id

        # Record contribution (ignore duplicate via savepoint)
        try:
            nested = self.db.begin_nested()
            contrib = GlobalProspectContribution(
                user_id=user_id,
                global_prospect_id=gp.id,
            )
            self.db.add(contrib)
            self.db.flush()
        except IntegrityError:
            nested.rollback()
