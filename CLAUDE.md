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
- 아직 안 한 것: 실제 수집/발송 end-to-end 테스트, 배포, 결제 연동 (PG사), pytest 테스트

## 주의사항
- bcrypt 직접 사용 중 (security.py) — passlib 제거됨
- Python 3.14는 pydantic-core wheel 없음 → Python 3.13 venv 사용
- MartMart_AD 폴더는 절대 수정하지 않음 (참고만)
- SECRET_KEY, ENCRYPTION_KEY는 .env에서 관리 (프로덕션에서는 반드시 변경)
- Supabase 연결 시 connection pooler 사용 (포트 6543, Transaction mode)
- 수집/이메일 발송 상태는 DB(CollectionJob, EmailSendJob)에 저장

## DB 테이블
**기존**: users, projects, keywords, prospects, email_logs, dm_logs, user_settings, collection_jobs, email_send_jobs
**Phase 1**: usage_records, subscriptions
**Phase 2**: prospect_notes, tags, prospect_tags
**Phase 3**: email_templates, email_variants, email_sequences, email_sequence_steps, sequence_enrollments
**Phase 4**: pipeline_stages, deals, call_logs, activities, proposals, proposal_templates, meeting_slots, meetings
**Phase 5**: onboarding_progress, teams, team_members, team_projects, api_keys

## API 엔드포인트 요약
- POST /api/auth/signup, /login, GET /me
- GET /api/dashboard/stats (대시보드 통계)
- POST/GET /api/projects/ (description 필드 포함)
- POST /api/projects/:id/keywords/ (단일 키워드: {keyword: "텍스트"})
- POST /api/projects/:id/collect/ (sources 파라미터 지원)
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
- **Phase 1: 수익화**
- GET /api/subscription/ (구독 정보)
- POST /api/subscription/upgrade, /downgrade (플랜 변경)
- GET /api/subscription/usage (사용량 조회)
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
