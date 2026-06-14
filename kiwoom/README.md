# kiwoom — Kiwoom Data API

키움 REST API 데이터 조회 전용 서버 (FastAPI, localhost :8001).
jongalab 메인 앱이 `core.kiwoom_client.KiwoomRestClient` 로 HTTP 호출한다.

```
uv run uvicorn api:app --host 127.0.0.1 --port 8001
```
