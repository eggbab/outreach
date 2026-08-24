#!/usr/bin/env bash
# Outreach SaaS — 비밀 키 생성 도우미
# 사용법: bash scripts/generate_keys.sh
# 출력된 두 줄을 .env 파일의 SECRET_KEY=, ENCRYPTION_KEY= 에 붙여넣으세요.

set -e

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3가 필요합니다." >&2
  exit 1
fi

# cryptography 패키지 (Fernet 키 생성용) 자동 설치
python3 -c "import cryptography" 2>/dev/null || {
  echo "ℹ️  cryptography 패키지 설치 중..."
  python3 -m pip install --quiet --user cryptography || pip3 install --quiet cryptography
}

SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

cat <<EOF

✅ 새로운 비밀 키 2개를 생성했습니다.
─────────────────────────────────────────────────
SECRET_KEY=$SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY
─────────────────────────────────────────────────

📝 다음 단계:
1) 프로젝트 폴더에 .env 파일이 없으면:  cp .env.example .env
2) .env 파일을 열어서 위 두 줄을 SECRET_KEY=, ENCRYPTION_KEY= 자리에 붙여넣으세요.
3) DATABASE_URL, BASE_URL, CORS_ORIGINS 도 본인 값으로 채우세요.

⚠️  이 키가 외부에 노출되면 사용자 데이터가 위험해집니다. .env는 절대 git에 커밋하지 마세요.
EOF
