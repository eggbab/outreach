# Outreach SaaS — B2B 영업 자동화 플랫폼

## 프로젝트 개요
김우진님의 개인용 B2B 영업 도구(MartMart_AD)를 웹 SaaS + 크롬 확장으로 사업화.
- 핵심: 키워드 → 잠재고객 수집 → 이메일/인스타 DM 발송 올인원
- 타겟: 한국 B2B 영업자

## 기존 코드 참고 (수정 금지)
`/Users/woojin/Documents/workspace/MartMart_AD/` — 원본 개인용 도구
- `마트마트_자동화.py` → 네이버/구글/인스타 수집 로직 참고
- `통합발송.py` → 이메일 SMTP + DM 템플릿 참고
- `인스타_DM_자동화.js` → 크롬 확장 content script 참고

## 기술 스택
- **백엔드**: Python 3.13 (venv), FastAPI, SQLAlchemy, PostgreSQL (Supabase), JWT(python-jose), bcrypt
- **프론트**: React + Vite + Tailwind CSS + lucide-react
- **크롬 확장**: Manifest V3, Instagram Private API

## 프로젝트 구조
```
backend/
├── app/
│   ├── api/           # auth, projects, keywords, prospects, collect, email_send, chrome, settings
│   ├── core/          # config, database(PostgreSQL/Supabase), security(JWT+bcrypt+Fernet암호화)
│   ├── models/        # SQLAlchemy 모델 (User, Project, Keyword, Prospect, EmailLog, DmLog, UserSettings)
│   └── services/
│       ├── collector/  # naver.py, google.py, instagram.py, manager.py
│       └── sender/     # email.py (SMTP)
├── requirements.txt
└── venv/              # Python 3.13 가상환경 (설치 완료)

frontend/
├── src/
│   ├── pages/         # LoginPage, SignupPage, DashboardPage, ProjectDetailPage, SettingsPage
│   ├── components/    # Layout(사이드바), ProspectTable
│   └── lib/           # api.js(axios+JWT), auth.jsx(AuthContext)
├── package.json       # 의존성 설치 완료
└── vite.config.js     # /api → localhost:8000 프록시

chrome-extension/
├── manifest.json      # Manifest V3
├── popup/             # 로그인 UI
├── background.js      # 서비스 워커 (API 통신)
├── content-scripts/   # instagram-dm.js (DM 자동발송)
└── utils/api.js       # 서버 통신
```

## 실행 방법
```bash
# 백엔드
cd backend && source venv/bin/activate && uvicorn app.main:app --reload
# → http://localhost:8000/docs 에서 Swagger UI

# 프론트
cd frontend && npm run dev
# → http://localhost:5173

# 크롬 확장
# chrome://extensions → 개발자 모드 → chrome-extension/ 폴더 로드
```

## 현재 상태 (2026-03-20)
- Phase 1 (백엔드): ✅ 완료 — 10개 라우터, 9개 DB 테이블, 레이트 리미팅, 로깅
- Phase 2 (프론트): ✅ 완료 — 빌드 성공 (317KB JS, 23KB CSS), 프론트-백엔드 API 동기화 완료
- Phase 3 (크롬 확장): ✅ 기본 구조 완료 + 아이콘 생성
- **대규모 확장 (v2.0)**: ✅ 완료
  - 수익화 인프라 (플랜/트라이얼/사용량 제한)
  - 분석 & 태그 & 메모 & 스코어링
  - 이메일 자동화 (시퀀스 + A/B 변형 + 발송 건강도)
  - 영업 파이프라인 & CRM (칸반, 딜, 통화, 제안서, 미팅)
  - 온보딩 & 팀 & CSV 내보내기 & API 키
  - 총 19개 새 백엔드 파일, 16개 새 프론트 파일, 22개 새 DB 테이블
  - 빌드 성공 (424KB JS, 33KB CSS)
- **독점 데이터 플랫폼 (v3.0)**: ✅ 완료
  - 중앙 잠재고객 DB (GlobalProspect pool + 기여 추적 + 이메일 마스킹)
  - 업종별 벤치마크 (자동 집계 + 비교 API)
  - 키워드별 ROI 추적 + 소스별 ROI + 추천 엔진
  - 새 DB 테이블 4개, 새 백엔드 파일 4개, 새 프론트 페이지 1개
  - 프론트 빌드 성공
- **크레딧 모델 + 결제 (v4.0)**: ✅ 완료
  - 기간제 구독 → 크레딧 종량제 전환 (수집 1cr, 이메일 2cr, DM 3cr)
  - 가입 시 50 크레딧 무료, 4종 충전 패키지 (7천원~15만원)
  - 토스페이먼츠 테스트 결제 연동
  - 발송 안전 시스템 (Gmail 워밍업 4주, 인스타 6주, 위험도 표시)
  - deep email extraction (5단계 탐색: 메인→링크→하위경로→footer→mailto)
  - 수집 시 모든 소스 자동 사용 (네이버웹+쇼핑+지도, 구글)
- **해자 기능 + 배포 준비 (v5.0, 2026-08-24)**: ✅ 완료 — 설계 문서 `docs/superpowers/specs/2026-08-24-moat-features-design.md`
  - 정보통신망법 §50 컴플라이언스 자동화: 제목 `(광고)` 표기(설정 토글), 전송자 정보+수신거부 푸터, List-Unsubscribe One-Click 헤더, `/api/t/unsub/{tracking_id}` 수신거부 랜딩
  - 전역 수신거부 풀(GlobalUnsubscribe) — 발송 시 유저 블랙리스트+전역 풀 체크 (일반/시퀀스 모두)
  - 반응 데이터 피드백 루프: 발송/열람/클릭/답장 → GlobalProspect.email_validity_score·last_verified_at·times_replied 갱신, Prospect.score 실계산, discover 품질 정렬(`sort=quality`)
  - 답장 감지: Gmail IMAP 15분 폴링 → status='replied' + 시퀀스 자동 중단(enrollment 'stopped')
  - 워밍업 강제: `get_enforced_daily_limit()` — 발송 시점에 계정 나이 기반 한도 캡 + 오늘 발송분 차감
  - 시퀀스 발송 정비: 크레딧 차감 + 추적 픽셀 + 컴플라이언스 적용
  - 배포 수정: 프로덕션 dev 시크릿 기동 차단, schema_sync(create_all+컬럼 보정, alembic 미사용), .dockerignore 중첩 경로, Docker에 chrome-extension 포함, CORS 확장 origin 허용, 확장 alarms 권한, discover import 크레딧 차감, subscription self-upgrade 라우트 제거, bootstrap-first-admin은 ADMIN_EMAIL 제한
  - 테스트 135개 통과 (신규 30개 포함)
- 아직 안 한 것: 실배포 실행 (Render/도메인), 계좌이체 외 PG 연동, 바운스(반송) 자동 감지

## 배포
- **권장: Docker 단일 박스** — `docker compose up -d` (백엔드가 frontend/dist까지 서빙)
- **분리 배포**: 프론트는 Vercel/Netlify, 백엔드는 Render/Fly/EC2 (Dockerfile 그대로)
  - Vercel 사용 시: `VITE_API_BASE_URL=https://api.your-domain.com` 빌드 환경변수 + `vercel.json` rewrites의 `API_HOST_PLACEHOLDER` 교체
- **Vercel 단독 배포 불가** — playwright(chromium)·instagrapi가 Lambda 50MB 한도 초과, APScheduler가 serverless에서 동작 불가

## 주의사항
- bcrypt 직접 사용 중 (security.py) — passlib 제거됨
- Python 3.14는 pydantic-core wheel 없음 → Python 3.13 venv 사용
- MartMart_AD 폴더는 절대 수정하지 않음 (참고만)
- SECRET_KEY, ENCRYPTION_KEY는 .env에서 관리 — **ENV=production에서 기본값이면 기동 실패(의도됨)**
- Supabase 연결 시 connection pooler 사용 (포트 6543, Transaction mode)
- 수집/이메일 발송 상태는 DB(CollectionJob, EmailSendJob)에 저장
- POST 라우트는 trailing slash 없이 호출 권장 (있으면 307 리다이렉트)
- DB 스키마는 시작 시 `app/core/schema_sync.py`가 관리 (create_all + 신규 컬럼/enum 보정) — alembic 명령 사용 안 함
- 서버는 **단일 워커 필수** (APScheduler 인프로세스 — 워커 늘리면 시퀀스 중복 발송)
- SequenceEnrollment.status에 'stopped' 추가됨 (답장/수신거부로 자동 중단)

## DB 테이블
**기존**: users, projects, keywords, prospects, email_logs, dm_logs, user_settings, collection_jobs, email_send_jobs
**Phase 1**: usage_records, subscriptions
**Phase 2**: prospect_notes, tags, prospect_tags
**Phase 3**: email_templates, email_variants, email_sequences, email_sequence_steps, sequence_enrollments
**Phase 4**: pipeline_stages, deals, call_logs, activities, proposals, proposal_templates, meeting_slots, meetings
**Phase 5**: onboarding_progress, teams, team_members, team_projects, api_keys
**Phase 6**: global_prospects, global_prospect_contributions, industry_benchmarks, keyword_performances (+ Prospect에 global_prospect_id, keyword_id 추가)
**Phase 7**: credit_transactions, service_keys, blacklist
**Phase 8**: User에 is_active, reset_token, reset_token_expires_at, terms_accepted_at 컬럼 추가
**v5.0**: global_unsubscribes (+ EmailLog.replied_at, GlobalProspect.times_replied, UserSettings.ad_prefix_enabled/sender_info)

## 수익 모델
- 크레딧 종량제 (월 구독 없음)
- 크레딧 단가: 수집 1cr, 이메일 2cr, DM 3cr
- 가입 시 50 크레딧 무료
- 충전 패키지: 100cr(7,000원/70원), 300cr(19,500원/65원), 1,000cr(60,000원/60원), 3,000cr(150,000원/50원)
- 결제: 토스페이먼츠 (테스트 키: test_gck_docs_...)

## API 엔드포인트 요약
- POST /api/auth/signup (accept_terms 필수), /login, GET /me, POST /activate-key
- POST /api/auth/forgot-password, /reset-password (비밀번호 재설정)
- POST /api/admin/bootstrap-first-admin (최초 관리자 자기 승격)
- GET /api/admin/users (검색·페이지네이션), /users/:id, PATCH /users/:id (정지/플랜/admin)
- POST /api/admin/users/:id/grant-credits (사유 필수, 거래 내역 기록)
- DELETE /api/admin/users/:id, GET /api/admin/stats (매출·MRR·ARPU)
- GET /api/extension/download (크롬 확장 ZIP 다운로드)
- GET /api/chrome/dm-queue?project_id=N (확장이 폴링)
- POST /api/chrome/dm-result (확장이 결과 보고 → 자동 크레딧 차감)
- POST /api/projects/:id/dm/ping (확장 살아있음 신호)
- 인스타 DM 발송은 **크롬 확장만** 사용 — 서버에서 발송 라우트 없음 (벤 위험 회피)
- GET /api/dashboard/stats (대시보드 통계)
- POST/GET /api/projects/ (description 필드 포함)
- POST /api/projects/:id/keywords/ (단일 키워드: {keyword: "텍스트"})
- POST /api/projects/:id/collect/ (max_results 파라미터, 모든 소스 자동 사용)
- GET /api/projects/:id/collect/status (current/total 형식)
- GET /api/projects/:id/prospects/ (items/total_pages 형식)
- PATCH /api/projects/:id/prospects/:id (승인/거절)
- POST /api/projects/:id/send-email/ (이메일 발송)
- GET /api/projects/:id/send-email/status (발송 진행률)
- POST /api/projects/:id/send-test-email (테스트 발송)
- GET /api/projects/:id/dm/status (크롬 확장 연결 상태)
- GET /api/projects/:id/dm/queue (DM 대기열)
- GET /api/projects/:id/dm/log (DM 발송 로그)
- GET /api/chrome/dm-queue?project_id= (크롬 확장용)
- POST /api/chrome/dm-result (DM 결과 보고)
- GET/PUT /api/settings/ (사용자 설정)
- **크레딧/결제**
- GET/POST /api/t/unsub/:tracking_id (공개 수신거부 — 유저 블랙리스트+전역 풀 등록)
- ~~POST /api/subscription/upgrade, /downgrade~~ 제거됨 (결제 검증 없는 권한 상승 경로)
- GET /api/subscription/ (구독 + 크레딧 잔액)
- GET /api/subscription/usage (오늘 사용량)
- GET /api/subscription/credit-packages (충전 패키지 목록)
- POST /api/subscription/purchase-credits (크레딧 충전)
- GET /api/subscription/credit-history (크레딧 내역)
- POST /api/payments/prepare (토스 결제 준비)
- POST /api/payments/confirm (토스 결제 확인)
- GET /api/settings/safety-guide (발송 안전 가이드)
- **Phase 2: 분석/태그/메모**
- GET /api/projects/:id/analytics/email-stats, /email-stats/daily, /funnel
- CRUD /api/projects/:id/prospects/:id/notes/
- CRUD /api/tags/ + POST /api/tags/attach, /detach
- **Phase 3: 이메일 자동화**
- CRUD /api/templates/ + /variants + /variants/stats
- CRUD /api/projects/:id/sequences/ + /steps + /enroll + /enrollments
- POST /api/deliverability/check
- **Phase 4: CRM/파이프라인**
- CRUD /api/pipeline/stages, /deals, /deals/:id/move, /stats
- CRUD /api/projects/:id/calls/, /callbacks
- GET /api/projects/:id/prospects/:id/timeline/
- CRUD /api/proposals/, POST /:id/send, GET /view/:tracking_id (공개)
- CRUD /api/meetings/, /meeting-slots/, PUT /:id/cancel
- GET /api/book/:user_id/slots, POST /api/book/:user_id (공개 예약)
- **Phase 5: 온보딩/팀/API**
- GET /api/onboarding/, POST /complete-step, /dismiss
- CRUD /api/teams/, /invite, /members, /projects
- GET /api/projects/:id/export/prospects (CSV)
- CRUD /api/api-keys/
- **Phase 6: 독점 데이터 플랫폼**
- GET /api/discover/ (잠재고객 DB 검색, 이메일 마스킹, sort=popular|quality)
- GET /api/discover/stats (공개 통계)
- POST /api/discover/import (프로젝트로 가져오기)
- GET /api/benchmarks/ (업종별 벤치마크 목록)
- GET /api/benchmarks/{industry} (업종 상세)
- GET /api/projects/:id/analytics/comparison (내 성과 vs 업종 평균)
- GET /api/projects/:id/analytics/keyword-roi (키워드별 ROI)
- GET /api/projects/:id/analytics/source-roi (소스별 ROI)
- GET /api/projects/:id/analytics/recommendations (추천)

## 개발 컨벤션
- 한국어로 소통, 코드/변수명은 영어
- 백엔드 새 엔드포인트 추가 시: router 파일 생성 → main.py에 include → CLAUDE.md API 목록 업데이트
- 프론트 새 페이지 추가 시: pages/ 에 파일 생성 → App.jsx 라우트 추가
- DB 스키마 변경 시: models/models.py 수정 (Supabase PostgreSQL, SQLAlchemy create_all 자동 생성)
- 커밋 메시지: 한국어 또는 영어, 간결하게

## 커스텀 커맨드 (/.claude/commands/)
- `/dev` — 백엔드+프론트 개발 서버 동시 실행
- `/test-backend` — 백엔드 API 테스트
- `/build` — 프론트엔드 빌드
- `/db-reset` — DB 초기화
- `/status` — 프로젝트 전체 상태 점검

## 사업화 플랜
- Phase 0: 에이전시 수익 검증 (기존 도구로 서비스 판매)
- Phase 1: 백엔드 ✅
- Phase 2: 프론트엔드 ✅
- Phase 3: 크롬 확장 ✅ (기본)
- Phase 4: 마케팅 & 런칭 (블로그, 가격 정책, 결제 연동)

## 스킬을 먼저 확인한다

- 요청을 받으면 **설치된 스킬 중 그 작업에 맞는 것이 있는지 먼저 확인한다.** 있으면 "이건 `/스킬명`으로 하겠습니다 — 이유" 한 줄을 붙이고 그 스킬을 호출해서 진행한다. 추천만 하고 멈추지 않는다.
- 사용자가 이미 `/명령어`로 부른 경우엔 추천하지 않는다.
- 맞는 스킬이 없으면 아무 말 없이 그냥 처리한다. 억지로 갖다 붙이지 않는다.
- **미설치 스킬·플러그인도 추천 대상이다. 공식이든 커뮤니티든 가리지 않는다.**
- **조회 대상은 `~/.claude/skill-catalog-measured.tsv` 하나다** — 마켓 11곳 카탈로그 2,709개에 측정값(별점·코드검색·설치횟수)을 붙인 표. `awk -F'\t'` 로 훑으면 끝난다. 판단 기준과 지표의 한계는 `~/.claude/popular-claude-skills.md` 에 있다. 여기 없는 것만 웹으로 찾는다.
- **인기도(사용량)는 공식·커뮤니티 모두에 똑같이 적용한다.** 많이 쓰인다는 것이 유용성이자 안정성의 방증이다. 설치 횟수가 있으면 그것, 없으면 별점 — **실측**한다(디렉터리 사이트 별점은 실제와 크게 다르다).
- **출처는 '안전성'에만 쓴다.** 공식(`claude-plugins-official`·`anthropic-agent-skills`·`claude-community`)은 그대로 추천. 커뮤니티는 **남의 지시문이 Claude 행동을 바꾸고 훅이 명령을 실행한다는 점을 설치 권할 때 함께 알린다.**
- **추천까지만 하고 설치는 사용자가 결정한다.** 미설치 항목을 임의로 설치하지 않는다. (설치된 스킬 호출은 이 제한과 무관 — 바로 실행한다.)
- **추천 전 3가지를 확인한다:** ① 그 도구가 실제로 뭘 하는지 파일을 열어볼 것 ② 이 프로젝트가 그 기능을 실제로 쓰는지 `grep` 으로 확인할 것(단어만 등장 ≠ 실사용) ③ 실행 준비물이 깔려 있는지 확인할 것(설치됨 ≠ 작동함).
- **운영 환경에 닿는 MCP는 기본적으로 추천하지 않는다.** 이 프로젝트는 Supabase(PostgreSQL)를 쓰므로 DB 직결 MCP는 특히 주의.
- 카탈로그에도 없으면 웹에서 찾아 알린다.
- **카탈로그 갱신은 사용자가 요청할 때만 한다.** 자동 갱신 훅을 걸지 않는다. 갱신 절차는 `skill-catalog-refresh` 스킬에 있다.
- 이 항목은 "물어본 것만 답한다" 원칙의 유일한 예외다.

> **적합성 판단 기준(이 프로젝트):** Python 3.13 · FastAPI · SQLAlchemy · PostgreSQL(Supabase) · JWT/bcrypt · React + Vite + Tailwind · 크롬 확장(Manifest V3) · Instagram Private API.
