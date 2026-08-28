# Outreach SaaS — B2B 영업 자동화 플랫폼

## 프로젝트 개요
김우진님의 개인용 B2B 영업 도구(MartMart_AD)를 웹 SaaS + 크롬 확장으로 사업화.
- 핵심: 키워드 → 잠재고객 수집 → 이메일/인스타 DM 발송 올인원
- 타겟: 한국 B2B 영업자

## 기존 코드 참고 (수정 금지)
`/Users/woojin/Documents/workspace/MartMart_AD/` — 원본 개인용 도구
- `마트마트_자동화.py` → 네이버/구글/인스타 수집 로직 참고 (현존)
- (참고: 과거 CLAUDE.md가 언급하던 `통합발송.py`·`인스타_DM_자동화.js`는 원본에 없음. DM 구현은 `chrome-extension/content-scripts/instagram-dm.js`가 정본)

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
  - 가입 시 30 크레딧 무료, 4종 충전 패키지 (7천원~15만원)
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
- **v5.1 (2026-08-24)**: 카카오 로컬 공식 API 수집 채널 (KAKAO_REST_API_KEY, 파이프라인 최우선·차단 리스크 0), 이메일 MX 검증(email_valid 채움 + 발송 시 invalid 스킵), 수집 파이프라인 중복 호출 버그 수정, GlobalProspect.region 사용 시작, 랜딩 허위 후기/수치 제거(표시광고법) + "왜 Outreach인가" 섹션. 네이버 지도 수집은 응답 가로채기 방식(캡차 우회)
- **v5.2 인스타 DM 재건 (2026-08-25)**: DM 발송이 구조적으로 0건이던 3대 결함 수정 — (1) username→인스타 PK 해석(content script가 web_profile_info로 조회, Prospect.instagram_pk 캐싱) (2) 큐 payload 계약 정합({prospect_id,username,instagram_pk,message,daily_limit}) (3) dm-result 계약 정합. 안티밴: 스핀택스 변형 실구현(`services/dm_compose.py`, 대상마다 다른 문구), DM 워밍업 서버 강제(chrome.py에서 get_enforced_daily_limit), 발송 시 블랙리스트/전역수신거부 체크, feedback_required/429/checkpoint 구조적 감지 + 6시간 쿨다운. 보안: dm-queue/dm queue IDOR 수정. 핸들 정규화 공용화(`extract.normalize_instagram` — 수집·수동입력·DM큐 일관). DmLog에 message_body·replied_at. DM 워밍업 첫날 0→3(서비스가입일 기준 한계 보정). 크롬확장 heartbeat 알람 추가. 테스트 155개 통과(DM 계약 테스트 신규)
- **v5.3 DM 안전성 강화 (2026-08-25)**: 시간당 한도 확장 강제(큐가 hourly_limit·min/max_delay 전달), 야간(21~08시) 발송 자동 차단(정보통신망법 §50③ + 봇패턴 회피), 연속 실패 3회 시 자동 중단, 삭제/비공개 계정(ACCOUNT_NOT_FOUND) 큐에서 영구 제외(무한재시도 방지). 확장 다운로드 시 서버 BASE_URL을 manifest host_permissions·popup 기본주소에 자동 주입(사용자가 manifest 수동편집 불필요). 리스크 고지 강화(콜드DM 비공식·밴 위험 정직 안내). 테스트 157개.
  - **인스타 DM 근본 한계(문서화)**: 콜드 DM은 공식 API 불가(먼저 연락한 사용자에게만 허용) → 비공식 방식만 가능 → 분기당 밴 위험 11~17% 존재. 안전장치로 최소화하되 제거 불가. 오래된 계정+소량 발송 권장. DmSendJob(서버측 발송 작업 기록) 없음 — 확장 로컬 상태로 재개하므로 세션 끊김 시 수동 재시작 필요
- **v5.4 데이터무결성·기능완성 (2026-08-25)**: 감사 2건(데이터무결성/기능완성)으로 발견한 P0·죽은기능 수정.
  - **P0 크레딧 원자성**: deduct/add_credits를 원자적 조건부 UPDATE로 (동시 수집+발송 시 lost update/음수/이중차감 방지)
  - **P0 stuck-running reaper**: `core/job_reaper.py` — 재시작 시 running으로 멈춘 CollectionJob/EmailSendJob을 failed 정리(수집 영구차단 방지) + 스케줄러 30분 주기 재확인
  - **P0 결제 이중승인 방지**: payment approve를 조건부 UPDATE로 멱등화, DM dm-result에서 크레딧 부족 시 success→failed 강등(무과금 발송 차단)
  - **거짓광고 제거**: "AI 스코어링"→"리드 스코어링", "A/B 테스트"→"수신자별 문구 자동 변형"(실구현: 이메일 발송에 스핀택스 적용), Hero 허위수치 제거, 카카오 발송=로드맵 명시
  - **죽은 기능 연결**: 제안서 send가 추적링크 담긴 실제 이메일 발송, 답장률(replied)을 대시보드·funnel에 추가(실제 전환신호)
  - **인덱스**: prospects(project_id,status)·email_logs(user_id,status)·dm_logs 등 hot 컬럼 인덱스(schema_sync)
  - 테스트 167개
- **v5.5 CRM 완성 (2026-08-25)**: 미팅 예약 확인 메일(예약자+호스트) + T-24h 리마인더(스케줄러 1h), 이메일 바운스 자동감지(`services/bounce_detector.py` — IMAP으로 mailer-daemon 반송 파싱 → email_valid=False로 재발송 차단, 하드바운스는 크레딧 환불(tx_type=refund)+전역 수신거부 등록, 스케줄러 30분). 테스트 175개.
- **v5.6~5.7 기능확장 (2026-08-25)**:
  - 딜리버러빌리티: SPF/DKIM/DMARC 실 DNS 검사(`services/dns_auth.py`) + 설정 UI(DomainAuthCheck)
  - A/B 테스트 완전구현: 발송 시 변형 weight 선택+variant_id 기록, EmailSendJob.template_id, TemplatesPage 변형편집+성과통계
  - 알림/할일: TaskItem 모델+CRUD(`/api/tasks`), TasksPage(사이드바 "할 일"), 마감 24h전 이메일 리마인더(스케줄러)
  - 스마트 발송시간: `services/smart_send.py` — 업종 best_send_hour 벤치마크에 자동 예약(주말·야간 회피), 데이터 부족 시 B2B 기본 오전10시. 발송 UI "최적 시간 자동 발송" 버튼
  - 테스트 198개
- **v5.8 통합점검 수정 (2026-08-25)**: 세션 코드 통합감사로 발견한 P0/P1 수정.
  - **P0 바운스 재환불 버그**: 30분 폴링마다 같은 반송을 재환불하던 것 — email_valid=False 처리분 스킵 + 전역차단 여부로 1회만 환불(멱등)
  - **타임존 통일**: `utcnow()`를 naive-UTC로 변경(전 컬럼/스케줄러 일관), scheduler의 aware now 전부 naive화. SQLite에서 aware/naive 혼재 문자열비교 오작동 제거
  - **job_reaper 오살 수정**: 예약발송 실행 시 started_at 리셋 — 미래예약이 시작 즉시 90분기준에 걸려 failed 되던 것 방지
  - **스마트발송 KST**: best_hour를 KST 벽시계로 해석→UTC 변환 저장(스케줄러 비교 정합). 실검증: KST 10시=UTC 01시 예약 확인
  - 테스트 199개. 브라우저 E2E(할일 토글, 도메인인증 100점, 스마트발송 예약) 실동작 확인
- **v5.9 실환경 E2E로 발견한 배포차단 버그 3건 (2026-08-28)**: Cloudflare 터널로 실제 HTTPS 공개 후 브라우저로 전 화면을 눌러보며 발견. 셋 다 **어느 호스팅에 올려도 터졌을** 버그.
  - **P0 회원가입 전면 실패**: 기존 DB에 `users.is_admin` 등 컬럼 10개 누락 → signup 500. 원인은 `schema_sync._ADDED_COLUMNS`가 **손으로 적는 목록**이라 모델에 컬럼을 추가하고 목록에 적는 걸 잊으면 조용히 누락되던 것. → **모델 metadata와 DB를 비교해 자동 보정**하도록 변경(목록 폐지). NOT NULL은 기본값이 있을 때만 백필 후 부여. `Base.metadata`가 비어 있으면 예외(모델 import 누락 시 조용한 no-op 방지)
  - **P0 HTTPS 뒤에서 앱 전체 먹통**: uvicorn이 `X-Forwarded-Proto`를 무시해(`--forwarded-allow-ips` 기본값이 127.0.0.1) 307 리다이렉트가 `http://`로 나가고 브라우저가 혼합 콘텐츠로 차단 → 프로젝트 생성·온보딩 등 실패. → Dockerfile CMD에 `--proxy-headers --forwarded-allow-ips *` 추가. 프론트의 `/onboarding` 호출도 끝 슬래시로 정정
  - **P1 분석 화면 500**: PG enum `prospect_status`에 `replied` 누락(`subscription_plan.personal`도). enum 값 목록도 손으로 적던 것 → **모델 Enum에서 자동 감지**로 변경
  - 회귀 테스트 `tests/test_schema_sync.py` 4건 추가(고의로 무력화해 실패 확인). 테스트 203개
  - 배포 도구 추가: `deploy/docker-compose.prod.yml`(Caddy 자동 HTTPS + 로그 용량 제한), `deploy/setup-server.sh`(도커 설치·방화벽), `deploy/free-test.sh`(맥에서 0원으로 공개 테스트)
- **알려진 미해결(감사 기록)**: A/B 승자 자동선택, TeamProject 접근제어 미연결(에이전시 공유 불가)·크레딧 풀링 없음(현단계 불필요 판단), IMAP 다유저 순차처리(대규모 시 스케일 이슈)
- 아직 안 한 것: 실배포 실행, 계좌이체 외 PG, DM 답장추적(인스타), DmSendJob 서버측 기록

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
- DB 스키마는 시작 시 `app/core/schema_sync.py`가 관리 — alembic 명령 사용 안 함. **모델 정의와 DB를 비교해 누락 컬럼·enum 값을 자동 보정**하므로, 모델에 컬럼/enum 값을 추가할 때 별도로 등록할 목록은 없다(손수 적던 방식은 v5.9에서 폐지)
- 서버는 **단일 워커 필수** (APScheduler 인프로세스 — 워커 늘리면 시퀀스 중복 발송)
- **HTTPS 앞단에 프록시(Caddy/Cloudflare/Render 등)를 두면 uvicorn에 `--proxy-headers --forwarded-allow-ips *` 필수** — 없으면 리다이렉트가 http로 나가 브라우저가 차단한다(Dockerfile에 반영됨)
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
- 가입 시 30 크레딧 무료
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

**규칙 전문은 `~/.claude/CLAUDE.md` 에 있다**(모든 프로젝트 공통, 자동 로드). 여기에 복사해두지 않는다.

> **이 프로젝트 적합성 기준:** Python 3.13(backend/venv) · FastAPI · SQLAlchemy · PostgreSQL(Supabase) · JWT/bcrypt · beautifulsoup4 · apscheduler · React + Vite + Tailwind · react-three-fiber · 크롬 확장(Manifest V3) · Instagram Private API
> **중복 확인 대상:** 명령어 `/build` `/db-reset` `/dev` `/status` `/test-backend`
