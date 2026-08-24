#!/usr/bin/env bash
# Outreach SaaS — 배포 전 .env 점검
# 사용법: bash scripts/check_env.sh

set -e

ENV_FILE="${1:-.env}"
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ $ENV_FILE 파일이 없습니다. 먼저: cp .env.example .env"
  exit 1
fi

# shellcheck disable=SC1090
set -a; source "$ENV_FILE"; set +a

errors=0
warn() { echo "  ⚠️  $1"; }
err()  { echo "  ❌ $1"; errors=$((errors+1)); }
ok()   { echo "  ✅ $1"; }

echo "── .env 점검 ──"

[ "$ENV" = "production" ] && ok "ENV=production" || warn "ENV가 production이 아닙니다 (현재: $ENV)"

case "$SECRET_KEY" in
  ""|"change-me-in-production"|"your-secret-key-here"|"dev-secret-key-change-in-production-please")
    err "SECRET_KEY가 기본값입니다. bash scripts/generate_keys.sh 로 새로 만드세요." ;;
  *) [ ${#SECRET_KEY} -ge 32 ] && ok "SECRET_KEY 설정됨" || err "SECRET_KEY가 너무 짧음 (32자 이상 권장)" ;;
esac

case "$ENCRYPTION_KEY" in
  ""|"change-me-in-production"|"your-fernet-key-here"|"fvYHhX1aPMMv9eWsM9vCMOSgADtfnXOgz17qb_ZlKI0=")
    err "ENCRYPTION_KEY가 기본값/예시입니다. bash scripts/generate_keys.sh 로 새로 만드세요." ;;
  *) ok "ENCRYPTION_KEY 설정됨" ;;
esac

case "$DATABASE_URL" in
  ""|*"localhost"*|*"password@db.xxxx"*) err "DATABASE_URL이 기본/예시 값입니다. Supabase 등 실제 DB 주소로 바꾸세요." ;;
  *) ok "DATABASE_URL 설정됨" ;;
esac

case "$BASE_URL" in
  ""|"http://localhost:8000"|"https://your-domain.com") warn "BASE_URL이 기본값입니다 (현재: $BASE_URL)" ;;
  *) ok "BASE_URL=$BASE_URL" ;;
esac

case "$CORS_ORIGINS" in
  ""|*"your-domain.com"*) warn "CORS_ORIGINS에 본인 도메인을 넣었는지 확인하세요." ;;
  *) ok "CORS_ORIGINS 설정됨" ;;
esac

case "$TOSS_SECRET_KEY" in
  ""|test_*) warn "토스 키가 테스트용입니다. 실 결제하려면 토스에서 라이브 키를 받아 교체하세요." ;;
  *) ok "토스 라이브 키로 보입니다" ;;
esac

# 인스타 DM은 이제 크롬 확장으로 처리 — 환경변수 불필요
ok "인스타 DM = 크롬 확장 방식 (사용자가 사이트에서 직접 설치)"

echo "─────────────"
if [ $errors -gt 0 ]; then
  echo "❌ 치명 오류 $errors개. 위 항목을 먼저 고치세요."
  exit 1
fi
echo "✅ 배포 준비 OK (경고는 선택)"
