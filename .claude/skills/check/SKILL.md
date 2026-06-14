---
name: check
description: 프론트(tsc + eslint)와 백엔드(py_compile) 품질 게이트를 일괄 실행한다. 커밋/PR 전 필수 검증.
---

# /check

변경 사항을 커밋·PR 전에 일괄 검증한다. 테스트가 없으므로 이게 최소 게이트다.

1. 변경 파일 파악: `git status --short`
2. 프론트(`.ts/.tsx`) 변경이 있으면:
   - `cd jongalab/frontend && npx tsc --noEmit`
   - `cd jongalab/frontend && npm run lint`
3. Python(`.py`) 변경이 있으면 각 파일에 대해:
   - `uv run --directory jongalab python -m py_compile <file>`
4. 라우터/API 응답을 바꿨으면 `/run-api` 로 띄워 `curl` 검증까지 권장.

실패가 있으면 **수정 후 다시 `/check`** 를 통과시킨 뒤에만 완료로 보고한다.
모든 단계 결과를 통과/실패로 요약해서 보고한다.
