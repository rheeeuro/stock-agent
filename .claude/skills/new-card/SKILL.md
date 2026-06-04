---
name: new-card
description: 모바일 우선 recharts 대시보드 카드 컴포넌트를 스캐폴드한다. 인자로 컴포넌트 이름(PascalCase)을 받는다.
---

# /new-card <Name>

`frontend/components/<Name>.tsx` 에 새 대시보드 카드를 만든다.

규칙:
- **모바일 우선**: 기본 스타일은 작은 화면 기준, `sm:`/`md:` 로만 확장.
- props 타입은 `frontend/types/index.ts` 에 정의하고 백엔드 응답 shape 과 맞춘다.
- 기존 카드(`StockReportCard.tsx`, `MentionTreemapCard.tsx`, `DailySummaryCard.tsx`)의
  컨테이너/패딩/다크모드 패턴을 그대로 따른다.
- 차트는 recharts, 아이콘은 lucide-react.

절차:
1. 기존 카드 1~2개를 읽어 현재 스타일 컨벤션(클래스, 다크모드 `dark:`)을 파악.
2. `types/index.ts` 에 props 인터페이스 추가.
3. `<Name>.tsx` 생성 — 데이터 없을 때/로딩 상태 처리 포함.
4. 사용할 페이지(`app/*/page.tsx`)에 import 안내.
5. `npx tsc --noEmit` 으로 타입 검증.
