#!/usr/bin/env bash
# 새 우분투 서버(오라클 무료 VM 등)를 배포 가능한 상태로 만든다.
# 서버에 SSH로 접속한 뒤 한 번만 실행:
#
#   curl -fsSL https://raw.githubusercontent.com/eggbab/outreach/master/deploy/setup-server.sh | bash
#
# 하는 일: 도커 설치 → 방화벽에서 80·443 열기 → 저장소 내려받기.
# 실제 실행은 이 스크립트가 끝난 뒤 안내하는 대로 .env를 채우고 compose up.
set -euo pipefail

REPO="${REPO:-https://github.com/eggbab/outreach.git}"
DIR="${DIR:-$HOME/outreach}"

say() { printf '\n\033[1;36m▶ %s\033[0m\n' "$*"; }

say "1/4  시스템 업데이트"
sudo apt-get update -qq
sudo apt-get install -y -qq ca-certificates curl git

say "2/4  도커 설치"
if command -v docker >/dev/null 2>&1; then
  echo "이미 설치돼 있음 — 건너뜀"
else
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
  echo "도커 설치 완료. (이 셸에서 바로 쓰려면 재로그인 필요)"
fi

# 오라클 우분투 이미지는 22번 말고 전부 막혀 있다. 이걸 안 열면
# 인증서 발급(80)도 실패하고 사이트도 안 열린다 — 가장 흔한 함정.
say "3/4  방화벽에서 80·443 열기"
for port in 80 443; do
  if sudo iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null; then
    echo "  $port 이미 열림"
  else
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport "$port" -j ACCEPT
    echo "  $port 열었음"
  fi
done
sudo apt-get install -y -qq iptables-persistent >/dev/null 2>&1 || true
sudo netfilter-persistent save >/dev/null 2>&1 || sudo sh -c 'iptables-save > /etc/iptables/rules.v4' || true
echo "  규칙 저장 완료 (재부팅해도 유지)"

say "4/4  소스 내려받기"
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" pull --ff-only
else
  git clone --depth 1 "$REPO" "$DIR"
fi

cat <<EOF

────────────────────────────────────────────────────────
서버 준비 완료.

⚠️  아직 남은 것 — 오라클 웹 콘솔에서도 포트를 열어야 합니다.
    Networking → Virtual Cloud Networks → (내 VCN) → Security Lists
    → Add Ingress Rules 로 80, 443 (Source 0.0.0.0/0) 추가.
    이 서버 안에서만 열어봐야 소용없습니다. 두 군데 다 열어야 합니다.

그다음:
    cd $DIR/deploy
    cp .env.example .env
    nano .env                 # 값 채우기
    docker compose -f docker-compose.prod.yml up -d --build

빌드는 10~20분 걸립니다 (크롬 내려받느라).
확인:
    docker compose -f docker-compose.prod.yml logs -f app
────────────────────────────────────────────────────────
EOF
