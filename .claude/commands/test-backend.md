백엔드 API를 테스트합니다.

1. backend 디렉토리의 venv를 활성화합니다
2. pytest를 실행합니다 (테스트 파일이 있으면)
3. 테스트 파일이 없으면 주요 API 엔드포인트를 curl로 스모크 테스트합니다:
   - POST /api/auth/signup (테스트 계정)
   - POST /api/auth/login
   - GET /api/auth/me
   - POST /api/projects/
   - GET /api/projects/
4. 결과를 요약해서 보고합니다
