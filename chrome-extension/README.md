# Outreach Chrome 확장 — 배포 가이드

## 배포 전 manifest.json 수정 필수

`manifest.json`의 `host_permissions`를 실제 배포 도메인으로 교체하세요.

### 현재 (개발용)
```json
"host_permissions": [
  "https://www.instagram.com/*",
  "http://localhost:8000/*",
  "https://*.outreach.app/*"
]
```

### 배포 시 (예시)
```json
"host_permissions": [
  "https://www.instagram.com/*",
  "https://api.your-domain.com/*"
]
```

- `localhost:8000` 제거 (개발 전용)
- `*.outreach.app` 자리에 실제 서버 도메인 입력

## Chrome Web Store 출시 체크리스트

1. `manifest.json`의 `version` 증가 (예: `1.0.0` → `1.0.1`)
2. `host_permissions`에서 localhost 제거
3. 실제 배포 도메인으로 교체
4. ZIP 압축: `cd chrome-extension && zip -r outreach-extension.zip . -x "README.md"`
5. [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole) 업로드

## 사용자 흐름

1. 사용자가 확장 설치 → popup에서 서버 URL + 이메일/비밀번호 입력
2. 서버 URL은 `chrome.storage.local.serverUrl`에 저장됨
3. `host_permissions`에 해당 도메인이 포함되어야 fetch 작동

따라서 **확장이 통신할 모든 가능한 도메인**을 `host_permissions`에 미리 명시해야 합니다.
