---
name: run-web
description: Next.js 프론트엔드 dev 서버를 기동하고 라우트가 뜨는지 확인한다. UI 변경을 실제로 확인할 때 사용.
---

# /run-web

Next.js 프론트(`:3000`)를 dev 모드로 띄우고 확인한다.

1. 이미 떠 있는지: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000/market`
2. 아니면 백그라운드 기동: `cd jongalab/frontend && npm run dev` (run_in_background: true)
3. 컴파일 완료까지 기다린 뒤 대상 라우트에 `curl` 로 200 확인.
   주요 라우트: `/market` `/stocks` `/reports` `/sectors` `/feed`
4. 백엔드 데이터가 필요하면 먼저 `/run-api` 로 `:8000` 을 띄운다.

UI 변경은 **모바일 우선**으로 확인한다 — 작은 화면 레이아웃이 깨지지 않는지 우선 점검.
