#!/usr/bin/env bash
# 돈 안 쓰고 테스트하기 — 내 맥에서 서비스를 켜고 무료 임시 주소로 공개한다.
#
#   ./deploy/free-test.sh start   # 켜기 (주소를 알려준다)
#   ./deploy/free-test.sh url     # 지금 주소 다시 보기
#   ./deploy/free-test.sh logs    # 서버 기록 보기
#   ./deploy/free-test.sh stop    # 끄기
#
# 필요한 것: docker, cloudflared (brew install cloudflared)
# 주의: 맥이 켜져 있어야만 접속됩니다. 껐다 켜면 주소가 바뀝니다.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${TMPDIR:-/tmp}/outreach-free-test"
IMAGE="outreach-deploy:latest"
NAME="outreach-test-run"
mkdir -p "$WORK"

say() { printf '\n\033[1;36m▶ %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

start() {
  [ -f "$DIR/deploy/.env" ] || die "deploy/.env 가 없습니다. .env.example 을 복사해 값을 채우세요."
  command -v cloudflared >/dev/null || die "cloudflared 가 없습니다:  brew install cloudflared"

  say "1/3  임시 주소 받기"
  pkill -f "cloudflared tunnel --url http://localhost:8000" 2>/dev/null || true
  rm -f "$WORK/tunnel.log"
  nohup cloudflared tunnel --url http://localhost:8000 > "$WORK/tunnel.log" 2>&1 &
  local url=""
  for _ in $(seq 1 20); do
    sleep 2
    url=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$WORK/tunnel.log" 2>/dev/null | head -1) || true
    [ -n "$url" ] && break
  done
  [ -n "$url" ] || die "주소를 못 받았습니다. $WORK/tunnel.log 를 확인하세요."
  echo "$url" > "$WORK/url.txt"
  echo "  $url"

  # 받은 주소를 앱에도 알려줘야 로그인·링크가 제대로 동작한다.
  say "2/3  서비스 켜기"
  sed -e "s|^BASE_URL=.*|BASE_URL=$url|" \
      -e "s|^CORS_ORIGINS=.*|CORS_ORIGINS=[\"$url\"]|" \
      "$DIR/deploy/.env" > "$WORK/env"
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  docker run -d --name "$NAME" -p 8000:8000 --memory=2g --env-file "$WORK/env" "$IMAGE" >/dev/null

  say "3/3  뜰 때까지 기다리는 중"
  for _ in $(seq 1 30); do
    sleep 2
    if curl -sf -o /dev/null "http://localhost:8000/health"; then
      cat <<EOF

────────────────────────────────────────────
✅ 준비됐습니다.  $url

  ⚠️  맥이 켜져 있어야만 접속됩니다.
  ⚠️  껐다 켜면 주소가 바뀝니다 — 실제 고객에게
      보낸 메일의 수신거부 링크가 깨지므로, 이 주소로는
      대량 발송하지 마세요 (본인 테스트 발송만).

  끄기:  ./deploy/free-test.sh stop
────────────────────────────────────────────
EOF
      return 0
    fi
  done
  die "서비스가 안 뜹니다.  ./deploy/free-test.sh logs 로 확인하세요."
}

case "${1:-start}" in
  start) start ;;
  url)   cat "$WORK/url.txt" 2>/dev/null || die "켜져 있지 않습니다." ;;
  logs)  docker logs -f "$NAME" ;;
  stop)
    docker rm -f "$NAME" >/dev/null 2>&1 || true
    pkill -f "cloudflared tunnel --url http://localhost:8000" 2>/dev/null || true
    echo "껐습니다." ;;
  *) die "쓰는 법: $0 {start|url|logs|stop}" ;;
esac
