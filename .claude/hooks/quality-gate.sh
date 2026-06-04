#!/usr/bin/env bash
# PostToolUse 품질 게이트: 편집된 파일 종류에 맞춰 빠른 검증을 돌린다.
# exit 2 = 실패를 Claude 에 피드백(stderr). exit 0 = 통과/대상 아님.
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"

FILE=$(python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    print(d.get("tool_input",{}).get("file_path",""))
except Exception:
    print("")
' 2>/dev/null || echo "")

[ -z "$FILE" ] && exit 0

case "$FILE" in
  *frontend/*.ts|*frontend/*.tsx)
    OUT=$(cd "$ROOT/frontend" && npx tsc --noEmit 2>&1)
    if [ $? -ne 0 ]; then
      echo "❌ tsc 타입 체크 실패 (frontend):" >&2
      echo "$OUT" | tail -30 >&2
      exit 2
    fi
    ;;
  *.py)
    REL="${FILE#$ROOT/}"
    OUT=$(cd "$ROOT" && uv run python -m py_compile "$REL" 2>&1)
    if [ $? -ne 0 ]; then
      echo "❌ Python 컴파일 실패: $REL" >&2
      echo "$OUT" | tail -20 >&2
      exit 2
    fi
    ;;
esac

exit 0
