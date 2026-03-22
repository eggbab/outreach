백엔드와 프론트엔드 개발 서버를 동시에 실행합니다.

1. 백엔드: `cd backend && source venv/bin/activate && uvicorn app.main:app --reload`을 백그라운드로 실행
2. 프론트: `cd frontend && npm run dev`를 백그라운드로 실행
3. 두 서버의 상태를 확인하고 사용자에게 보고

서버가 이미 실행 중이면 중복 실행하지 않습니다.
