---
name: run-api
description: FastAPI 백엔드를 백그라운드로 기동하고 헬스 체크한다. API 동작 확인이나 엔드포인트 테스트가 필요할 때 사용.
---

# /run-api

FastAPI 백엔드(`:8000`)를 띄우고 살아있는지 확인한다.

1. 이미 떠 있는지 확인: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/docs`
   - 200/정상 응답이면 이미 기동된 것 → 그대로 사용.
2. 아니면 백그라운드로 기동:
   `uv run uvicorn api:app --host 127.0.0.1 --port 8000` (run_in_background: true)
3. 몇 초 후 `/docs` 또는 대상 엔드포인트에 `curl` 로 200 확인.
4. 검증 대상 엔드포인트가 있으면 `curl -s http://127.0.0.1:8000/<path>` 로 응답 shape 까지 확인하고 요약.

DB/Ollama 가 필요하면 `docker ps` 로 컨테이너 상태를 먼저 확인할 것.
