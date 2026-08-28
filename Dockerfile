FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
WORKDIR /app

# System dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget gnupg2 \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

# Backend code
COPY backend/ ./

# Frontend build
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Chrome extension (ZIP 다운로드 API가 서빙)
COPY chrome-extension/ ./chrome-extension/

# Insta sessions directory
RUN mkdir -p insta_sessions

EXPOSE 8000

# 스키마는 앱 시작 시 schema_sync가 관리 (alembic 마이그레이션은 초기 2개뿐이라 사용 안 함)
# 스케줄러 중복 실행 방지를 위해 단일 워커 필수 — 워커를 늘리려면 스케줄러 분리 필요
# --forwarded-allow-ips=*: 앞단 프록시(Caddy/Cloudflare/Render)가 붙여주는
# X-Forwarded-Proto를 신뢰해야 앱이 자기 주소를 https로 인식한다. 이게 없으면
# 307 리다이렉트가 http://로 나가 브라우저가 차단한다(혼합 콘텐츠).
# 컨테이너 포트는 프록시를 통해서만 노출되므로 *로 두어도 안전하다.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
