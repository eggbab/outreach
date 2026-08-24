# 배포 가이드 — 비개발자용 단계별 안내

이 문서는 사장님(김우진님)이 **처음 배포할 때** 쓰는 체크리스트입니다.

---

## ✅ 사전 준비 (한 번만)

| 무엇 | 어디서 | 비용 | 설명 |
|---|---|---|---|
| 도메인 | gabia.com | 1만~2만원/년 | 사이트 주소 (예: `mart-mart.kr`) |
| 데이터베이스 | supabase.com | 무료 | 회원 정보·잠재고객을 저장할 곳 |
| 서버 호스팅 | render.com | 7~25 USD/월 | 24시간 사이트가 떠있을 컴퓨터 |
| Gmail 앱 비밀번호 | google.com 보안 | 무료 | 이메일 자동 발송용 (IMAP 켜두면 답장 자동 감지도 됨) |
| 입금 계좌 | 본인 은행 | 무료 | 결제는 계좌이체 방식 — `.env`의 `BANK_*`에 입력 |

---

## 🚀 배포 5단계

### 1️⃣ 비밀 키 만들기
```bash
bash scripts/generate_keys.sh
```
출력된 `SECRET_KEY=`, `ENCRYPTION_KEY=` 두 줄을 복사해두세요.

### 2️⃣ `.env` 파일 만들기
```bash
cp .env.example .env
```
`.env`를 열어 아래 항목을 채웁니다.
- `DATABASE_URL=` ← Supabase에서 복사한 connection string
- `SECRET_KEY=` ← 1단계에서 받은 값
- `ENCRYPTION_KEY=` ← 1단계에서 받은 값
- `BASE_URL=https://본인도메인.kr`
- `CORS_ORIGINS=["https://본인도메인.kr"]`
- `ENV=production`
- `BANK_NAME=`, `BANK_ACCOUNT=`, `BANK_HOLDER=` ← 입금받을 계좌
- `ADMIN_EMAIL=본인이메일` ← 이 계정만 최초 관리자 승격 가능 (보안)
- `KAKAO_REST_API_KEY=` ← **강력 권장.** developers.kakao.com에서 5분이면 무료 발급.
  공식 API라 서버 IP가 차단될 걱정 없이 업체를 수집합니다 (일 10만 건 무료).
  네이버/구글 수집이 차단돼도 카카오 채널은 계속 동작합니다.

> `ENV=production`에서 SECRET_KEY/ENCRYPTION_KEY를 기본값으로 두면 **서버가 아예 시작하지 않습니다** (의도된 안전장치).

### 3️⃣ 환경 점검
```bash
bash scripts/check_env.sh
```
"✅ 배포 준비 OK"가 나와야 다음으로 갑니다. ❌가 있으면 위 단계로 돌아가서 고치세요.

### 4️⃣ Docker 빌드 (Render에서 자동 실행되므로 로컬에선 선택)
```bash
docker compose up -d --build
```
브라우저에서 `http://localhost:8000` 열어 화면이 나오면 OK.

### 5️⃣ Render에 올리기
1. GitHub에 코드 push
2. render.com → New → Web Service → 본인 저장소 선택
3. Runtime: **Docker** 선택
4. Environment variables 화면에 `.env`의 모든 줄을 한 줄씩 추가
5. Create Web Service → 5~10분 대기
6. Render가 준 주소(예: `outreach-xxx.onrender.com`)에 접속 → 회원가입까지 됨
7. 가비아 도메인 DNS → Render가 알려준 CNAME 추가 → 30분 뒤 본인 도메인으로 접속

---

## 🧪 배포 직후 본인이 직접 점검 (필수!)

배포된 사이트에서 **순서대로**:

- [ ] 회원가입 → 로그인 됨
- [ ] 프로젝트 만들기 → 키워드 추가 → 수집 시작 → 잠재고객이 모임
- [ ] 설정에서 Gmail 주소 + 앱 비밀번호 저장됨
- [ ] 본인 이메일 주소를 잠재고객으로 추가 → "테스트 발송" → 본인 메일함에 도착
- [ ] 메일 안의 링크 클릭 → 분석 페이지에서 클릭 카운트 +1
- [ ] 크레딧 충전 신청 (계좌이체 안내가 뜸) → 관리자 페이지에서 승인 → 크레딧 충전됨
- [ ] 받은 테스트 메일 하단 "수신거부" 클릭 → 블랙리스트에 자동 등록됨
- [ ] 본인 계정으로 `/api/admin/bootstrap-first-admin` 호출(관리자 페이지 안내) → 관리자 됨
- [ ] 로그아웃 → 다시 로그인 됨

**여기서 막히면 그게 진짜 버그입니다.** 캡처해서 오세요.

---

## 🔄 코드 업데이트 시
1. 로컬에서 수정 후 `git push`
2. Render는 자동으로 재배포 (1~5분)
3. 화면 새로고침 → 적용 확인

---

## 🛟 자주 쓰는 명령어

| 명령 | 용도 |
|---|---|
| `bash scripts/generate_keys.sh` | 새 비밀 키 발급 |
| `bash scripts/check_env.sh` | .env 점검 |
| `docker compose up -d` | 로컬에서 사이트 띄우기 |
| `docker compose logs -f` | 사이트 로그 실시간 보기 |
| `docker compose down` | 사이트 끄기 |
| `cd backend && pytest` | 자동 테스트 돌리기 |

---

## ⚠️ 주의

- **`.env` 파일은 절대 GitHub에 올리지 마세요.** `.gitignore`에 이미 들어 있어야 합니다.
- **크롬 확장**의 `chrome-extension/manifest.json`에서 `host_permissions`의 `*.outreach.app`을 본인 도메인으로 바꿔야 합니다.
- **Gmail은 하루 500통**이 한도입니다. 초과하면 계정 정지될 수 있어요. 신규 계정은 **워밍업 한도가 발송 시 자동 강제**됩니다 (첫날 5건부터 매일 +3건, 4주간).
- **광고 메일 법적 표기**: 제목 `(광고)` 표기와 수신거부 링크가 자동 삽입됩니다. 설정에서 회사명·주소·연락처(전송자 정보)를 꼭 입력하세요 — 정보통신망법 §50 필수 항목입니다.
- **서버는 단일 워커로 실행**됩니다 (Dockerfile). 워커를 늘리면 시퀀스 메일이 중복 발송되니 늘리지 마세요.
- DB 스키마는 서버 시작 시 자동 생성/보정됩니다 (`alembic` 명령 불필요).
