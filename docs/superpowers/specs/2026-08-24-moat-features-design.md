# 사업성 분석 & 해자(Moat) 기능 설계 — 2026-08-24

## 1. 사업성 분석

### 1.1 포지셔닝
"한국 시장 특화 올인원 아웃바운드" — 키워드 → 네이버/구글/지도 수집 → 이메일/DM 발송 → CRM 파이프라인까지 한 도구.

**글로벌 경쟁 (Apollo, Instantly, Lemlist, Salesforge):**
- 강점: 방대한 B2B DB, 멀티 메일박스 로테이션, AI 개인화.
- 약점(=우리 기회): **한국 로컬 데이터 없음.** 네이버 플레이스/쇼핑/지도 기반 소상공인·중소사업자는 글로벌 DB에 사실상 부재. 한국어 UI, 원화 결제, 정보통신망법 준수도 없음.

**2026 트렌드:** 물량전(spray-and-pray)에서 시그널 기반·정밀 타겟팅으로 이동. "누구에게 보내도 되는가(반응하는가)"라는 데이터 자체가 상품이 됨.

### 1.2 구조적 리스크 (사업성의 하방)
| 리스크 | 내용 | 완화책 |
|---|---|---|
| 법적 | 정보통신망법 §50: 광고성 정보는 사전 동의 원칙, `(광고)` 표기·전송자 정보·수신거부 방법 명시 의무. 현재 **전부 미구현** | 컴플라이언스 자동화 (M2) — 리스크 완화이자 세일즈 포인트 |
| 플랫폼 | SERP 스크래핑 차단(CAPTCHA/IP), Instagram 계정 벤 | 발송/수집 안전장치, 워밍업 강제 (M4) |
| 전달성 | 유저당 Gmail 1계정 → 대량 발송 시 스팸함 직행 | 워밍업 강제 + 수신거부/블랙리스트로 신고율 억제 |

### 1.3 해자 진단: 무엇이 진짜 해자인가
현재 코드베이스에서 **구조적 해자가 될 수 있는 유일한 자산은 `GlobalProspect` 공유 풀**이다 — 모든 유저의 수집이 중앙 DB에 쌓이고(`manager.py:228`), 발송·열람·클릭 결과가 업체별로 누적된다(`tracking.py`). 유저가 늘수록 "이 업체는 이메일이 살아있고 콜드메일에 반응한다"는 **검증된 반응 데이터**가 쌓인다. 이건 Apollo가 한국에서 절대 못 따라오는 데이터다.

**그러나 지금은 반쯤 죽어 있다:**
- `email_validity_score`, `last_verified_at`, `region` — 선언만 되고 아무도 안 씀 (`models.py:636`)
- `Prospect.score` 계산 함수(`scoring.py`)는 어디서도 호출 안 됨
- `discover` 가져오기는 크레딧을 **차감하지 않음** (수익 누수, `discover.py:200`)

기능 나열(CRM, 미팅, 제안서 등)은 해자가 아니다 — 복제 가능. 해자는 **(a) 쓸수록 좋아지는 데이터, (b) 규제 준수 자동화, (c) 발송 평판 보호**의 3축이다.

## 2. 해자 기능 설계 (이번 구현 범위)

### M1. 반응 데이터 피드백 루프 (데이터 네트워크 효과)
> 유저 A의 발송 결과가 유저 B의 타겟팅 품질을 높인다.

- 발송 성공 → `GlobalProspect.email_validity_score` 상승, `last_verified_at` 갱신
- 열람/클릭(이미 `times_opened/clicked` 집계 중) → **참여 점수(engagement)** 산출
- `deep_extract_email` 수집 시 최초 validity 부여
- `discover` 검색: 품질 점수 노출 + 정렬 옵션 (`sort=quality`)
- `scoring.py`를 수집 파이프라인에 실제 연결 → `Prospect.score` 채움
- **수익 누수 수선**: `discover/import` 크레딧 실제 차감

### M2. 정보통신망법 컴플라이언스 자동화 (규제 해자)
> "법적으로 안전한 콜드메일"을 파는 유일한 국내 툴이 된다.

- 발송 시 제목에 `(광고)` 자동 표기 (기본 ON, `UserSettings.ad_prefix_enabled`)
- 본문 하단에 전송자 정보 + 수신거부 링크 자동 삽입, `List-Unsubscribe`(+One-Click) 헤더
- `GET/POST /api/t/unsub/{tracking_id}` — 인증 없는 수신거부 랜딩 (한 클릭)
- 수신거부 시: 해당 유저 `Blacklist` 자동 등록 + **전역 수신거부 풀** `GlobalUnsubscribe` 테이블 기록
- **발송 시점 차단**: 유저 블랙리스트 + 전역 수신거부 풀 체크 (현재는 수집 시만 체크) — 유저가 늘수록 전체 스팸 신고율이 낮아지는 집단 방어 효과
- 시퀀스 발송에도 동일 적용

### M3. 답장 감지 (IMAP)
> 답장한 고객에게 후속 메일이 나가는 건 딜 킬러다. 현재 시퀀스는 답장을 몰라서 계속 보낸다.

- Gmail IMAP(993, 앱 비밀번호 재사용)으로 발송 이메일의 답장 폴링 (스케줄러 15분 주기)
- 발신자 매칭 → `Prospect.status='replied'` + `EmailLog.replied_at` + `SequenceEnrollment` 자동 중단(`stopped`)
- `GlobalProspect.times_replied` 누적 → M1 품질 점수에 최고 가중치 반영

### M4. 워밍업 강제 (발송 안전)
- `get_safe_daily_limit()`(계정 연령 기반 워밍업 곡선)은 이미 있으나 **안내만 하고 강제 안 함** → 발송 시 `min(사용자 설정, 워밍업 한도)` 적용
- 시퀀스/예약 발송에도 동일 적용

### 이번에 하지 않는 것 (YAGNI)
- AI 개인화 문구 생성 (별도 스프린트 — API 비용/UX 설계 필요)
- 멀티 메일박스 로테이션, 시그널 기반 트리거, 이메일 검증 외부 API
- 카카오톡 채널 연동

## 3. 배포 전 점검 — 발견 이슈 및 수정 계획

### P0 (배포 차단)
1. `SECRET_KEY`/`ENCRYPTION_KEY` dev 기본값으로 프로덕션 기동 허용 → **hard fail**로 변경 (`config.py:62`)
2. Alembic 마이그레이션 2개 vs 모델 33개 — `alembic upgrade head`가 스키마 대부분을 못 만듦 → 프로젝트 컨벤션(create_all)에 맞춰 **startup create_all을 전 DB로 확대** + Dockerfile CMD 수정
3. `.dockerignore` 중첩 경로 미보호 — `backend/.env`, `backend/venv`, `backend/outreach.db`가 이미지에 포함 → 패턴 수정
4. `discover/import` 크레딧 미차감 (수익 누수) → M1에서 수정
5. `deduct_credits` 반환값 무시 (`email.py:247`) — 잔액 부족 시 무과금 발송 → 수정
6. 시퀀스 발송: 크레딧 미차감 + 추적 픽셀 미삽입 + 컴플라이언스 미적용 (`scheduler.py:44`) → 수정

### P1 (기능 파손/보안)
7. 크롬 확장 `alarms` 권한 누락 — 서비스 워커 기동 실패 → manifest 수정
8. CORS에 `chrome-extension://` origin 미허용 → `allow_origin_regex` 추가
9. 확장 ZIP 다운로드가 Docker에서 404 — 이미지에 `chrome-extension/` 복사 + 경로 탐색 보강
10. `subscription` upgrade/downgrade — 결제 검증 없이 플랜 변경 가능 → 라우트 제거(크레딧 모델에서 무의미)
11. 발송 시 블랙리스트 미체크 → M2에서 수정
12. 스케줄러 다중 워커 중복 실행 → 단일 워커 전제 문서화 + uvicorn workers=1 확인

### P2 (품질)
13. 유령 배포 설정 정리: `backend/Dockerfile`, `frontend/Dockerfile`+`nginx.conf`, `vercel.json` placeholder
14. `bootstrap-first-admin` 레이스 → `ADMIN_EMAIL` env 일치 시에만 허용
15. `datetime.utcnow` deprecation, three.js 866KB 청크(lazy 유지 확인)

## 4. 새 DB 스키마
- `GlobalUnsubscribe`: id, email(unique, indexed), source_user_id, tracking_id, created_at
- `EmailLog.replied_at` (DateTime, nullable)
- `GlobalProspect.times_replied` (Int, default 0)
- `UserSettings.ad_prefix_enabled` (Bool, default True), `sender_info` (Text — 회사명/연락처 푸터용)

## 5. 테스트 전략
- 컴플라이언스: 제목 프리픽스·푸터·헤더 삽입 단위 테스트, unsub 엔드포인트 → 블랙리스트+전역 풀 등록 통합 테스트
- 크레딧: discover import 차감, 잔액 부족 시 발송 중단
- 피드백 루프: 발송/열람/답장 → GlobalProspect 점수 갱신
- 발송 차단: 블랙리스트/전역 수신거부 대상 스킵
- 기존 105개 테스트 회귀 통과 유지
