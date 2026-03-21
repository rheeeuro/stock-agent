"""
AI 프롬프트 템플릿 모듈 - YouTube/Telegram 공통 분석 프롬프트 관리
"""

# 공통 분석 지시사항 (YouTube, Telegram 모두 사용)
_COMMON_ANALYSIS_INSTRUCTIONS = """
[중요 지시사항]
먼저 이 메시지가 **'주식, 경제, 투자, 기업 분석, 시장 전망'**과 관련된 내용인지 판단해.

1. 만약 **관련 없는 내용(일상, 먹방, 게임, 단순 유머 등)**이라면:
   반드시 JSON의 sentiment_score를 **-1**로 설정하고 content는 비워둬.
   
2. **관련 있는 내용**이라면 다음 두 가지를 분석해서 반드시 **JSON 포맷**으로만 출력해.
    - sentiment_score: 시장 전망 점수 (0: 폭락/공포 ~ 50: 중립 ~ 100: 폭등/탐욕)
    - content: 마크다운 형식의 투자 인사이트 분석 리포트 (3줄 요약, 종목, 대응 전략 포함)
    - related_companies: 텍스트에서 언급된 주식 종목이 있다면, **기업의 공식 이름(영문)**을 리스트 형태로 추출할 것. (예: ["NVIDIA", "Tesla", "Samsung Electronics"]). 없으면 빈 리스트 [] 를 반환할 것.
        🚨주의: 반드시 '현재 주식 시장에 상장된 공식 기업'의 이름만 추출해라. Grok, OpenAI, ChatGPT 같은 제품명, AI 모델, 비상장 기업은 절대 포함하지 마라!
    - market: 이 메시지에서 주로 다루는 시장을 분류해라. (미국 주식이면 "US", 한국 주식이면 "KR", 암호화폐면 "CRYPTO", 애매하면 "UNKNOWN")

    [content는 반드시 아래 Markdown 형식을 지켜서 출력해]:
    
        ## 1. 3줄 핵심 요약
        - (요약 1)
        - (요약 2)  
        - (요약 3)
        
        ## 2. 주요 언급 종목
        - **종목명**: (호재/악재 판단)
        
        ## 3. 대응 전략
        > (한 줄 조언)
"""

_COMMON_JSON_FORMAT = """
[필수 출력 형식 - JSON Only]:
{{
    "sentiment_score": 75,  // 아닐 경우 -1
    "content": "분석 내용..." // 아닐 경우 ""
    "related_companies": ["NVIDIA"], // 아닐 경우 []
    "market": "US"
}}
"""

# YouTube 분석용 프롬프트 (title + content 플레이스홀더)
YOUTUBE_ANALYSIS_PROMPT = """
        영상 제목: {title}
""" + _COMMON_ANALYSIS_INSTRUCTIONS + _COMMON_JSON_FORMAT + """
        [자막 내용]: {content}
"""

# Telegram 분석용 프롬프트 (title 자동 생성 포함)
TELEGRAM_ANALYSIS_PROMPT = _COMMON_ANALYSIS_INSTRUCTIONS + """
    - title: 제목
""" + """
[필수 출력 형식 - JSON Only]:
{{
    "sentiment_score": 75,  
    "content": "분석 내용...", 
    "title": "제목",
    "related_companies": ["NVIDIA"], // 아닐 경우 []
    "market": "US"
}}

[메시지 내용]: {text}
"""

# 일일 요약 리포트 프롬프트
DAILY_DIGEST_PROMPT = """
[오늘의 리포트 데이터 시작]
{reports_text}
[오늘의 리포트 데이터 끝]

-----------------------
[시스템 절대 지시사항]
너는 위의 데이터를 분석해서 오직 JSON 형식으로만 응답하는 기계다.
영어는 절대 사용하지 말고 무조건 '한국어(Korean)'로만 작성해라.
인사말, 요약, 설명 등은 절대 금지한다.

[필수 출력 형식 - 그대로 복사해서 내용만 채울 것]:
```json
{{
    "buy_stock": "가장 추천하는 매수 종목명 1개",
    "buy_ticker": "매수 종목의 티커 심볼 (예: TSLA, NVDA, 005930.KS 등. 모르면 빈칸)",
    "buy_reason": "매수 추천 이유 1줄 요약",
    "sell_stock": "매도 또는 관망 종목명 1개",
    "sell_ticker": "매도 종목의 티커 심볼 (모르면 빈칸)",
    "sell_reason": "매도/관망 이유 1줄 요약"
}}
```
"""
