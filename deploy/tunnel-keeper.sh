#!/usr/bin/env bash
# 통로(터널) 감시견 — 끊기면 알아서 다시 연결한다.
#
# 무료 임시 통로(trycloudflare)는 클라우드플레어가 보장해주지 않는다.
# 몇 시간~하루 지나면 연결이 끊기고 스스로 복구되지 않는 경우가 있다.
# 이 스크립트가 1분마다 확인해서 죽었으면 새로 열고, 바뀐 주소를 앱에도 알려준다.
#
# free-test.sh 가 자동으로 띄우므로 직접 실행할 일은 없다.
set -uo pipefail

WORK="${1:?work dir}"
NAME="${2:-outreach-test-run}"
IMAGE="${3:-outreach-deploy:latest}"
ENV_SRC="${4:?env file}"

log() { printf '%s  %s\n' "$(date '+%m-%d %H:%M:%S')" "$*" >> "$WORK/keeper.log"; }

# 통로가 살아 있는지 확인. DNS가 늦게 퍼지는 경우가 있어 클라우드플레어 IP로 직접 찌른다.
tunnel_alive() {
  local url host ip
  url=$(cat "$WORK/url.txt" 2>/dev/null) || return 1
  [ -n "$url" ] || return 1
  host=${url#https://}
  ip=$(dig +short "$host" 2>/dev/null | grep -m1 -E '^[0-9.]+$')
  if [ -n "$ip" ]; then
    curl -sf -o /dev/null --max-time 12 --resolve "$host:443:$ip" "$url/health"
  else
    curl -sf -o /dev/null --max-time 12 "$url/health"
  fi
}

open_tunnel() {
  pkill -f "cloudflared tunnel --url http://localhost:8000" 2>/dev/null
  sleep 2
  : > "$WORK/tunnel.log"
  nohup cloudflared tunnel --url http://localhost:8000 >> "$WORK/tunnel.log" 2>&1 &
  local url=""
  for _ in $(seq 1 25); do
    sleep 2
    url=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$WORK/tunnel.log" | head -1)
    [ -n "$url" ] && break
  done
  [ -n "$url" ] || { log "새 통로 열기 실패"; return 1; }
  echo "$url" > "$WORK/url.txt"
  log "새 주소: $url"

  # 주소가 바뀌었으니 앱에도 알려준다 (로그인·수신거부 링크가 이 주소를 쓴다).
  sed -e "s|^BASE_URL=.*|BASE_URL=$url|" \
      -e "s|^CORS_ORIGINS=.*|CORS_ORIGINS=[\"$url\"]|" \
      "$ENV_SRC" > "$WORK/env"
  docker rm -f "$NAME" >/dev/null 2>&1
  docker run -d --name "$NAME" -p 8000:8000 --memory=2g --env-file "$WORK/env" "$IMAGE" >/dev/null
  log "앱 재시작 완료"
}

log "감시 시작"
fails=0
while true; do
  sleep 60
  # 앱이 죽었으면 앱부터 살린다.
  if ! curl -sf -o /dev/null --max-time 10 http://localhost:8000/health; then
    if ! docker ps --filter "name=$NAME" --format '{{.Names}}' | grep -q "$NAME"; then
      log "앱이 멈춰 있음 — 다시 켠다"
      docker start "$NAME" >/dev/null 2>&1 || open_tunnel
    fi
    continue
  fi
  if tunnel_alive; then
    fails=0
  else
    fails=$((fails + 1))
    log "통로 응답 없음 ($fails/2)"
    if [ "$fails" -ge 2 ]; then   # 일시적 실패로 성급히 주소를 바꾸지 않는다
      log "통로가 끊겼다고 판단 — 새로 연결"
      open_tunnel && fails=0
    fi
  fi
done
