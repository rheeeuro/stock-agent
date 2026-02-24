import mysql.connector
import requests
import json
import sys
import os
import re
from datetime import datetime
from ollama import Client

from dotenv import load_dotenv
load_dotenv()

# ==========================================
# [설정 1] 텔레그램 봇 정보 (본인 것으로 수정!)
# ==========================================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
CHAT_ID = os.getenv('CHAT_ID', '')
CHAT_ID2 = os.getenv('CHAT_ID2', '')

# ==========================================
# [설정 2] DB 연결 정보
# ==========================================
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'user': os.getenv('DB_USER', 'stock_user'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'stock_agent'),
    'port': int(os.getenv('DB_PORT', '3307')),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'use_unicode': True,
}

def send_telegram_alert(date, buy, buy_r, sell, sell_r):
    """텔레그램으로 요약 리포트 전송"""
    message = (
        f"📅 *[{date}] 오늘의 AI 투자 전략*\n\n"
        f"🐂 *매수(Buy): {buy}*\n"
        f"└ {buy_r}\n\n"
        f"🐻 *매도(Sell): {sell}*\n"
        f"└ {sell_r}\n\n"
        f"👉 [대시보드 확인하기](https://stock.rheeeuro.com)"
    )
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        chat_ids = [cid for cid in [CHAT_ID, CHAT_ID2] if cid]
        for chat_id in chat_ids:
            data = {
                "chat_id": chat_id,
                "text": message, 
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            requests.post(url, data=data, timeout=10)
        print(f"📨 텔레그램 전송 완료 -> {len(chat_ids)}개 채팅방")
    except Exception as e:
        print(f"❌ 텔레그램 전송 실패: {e}")

def generate_daily_report():
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # 1. 오늘(최근 24시간) 수집된 데이터 조회
        print("🔍 오늘의 데이터 조회 중...")
        query = """
            SELECT source_name, title, analysis_content, sentiment_score 
            FROM content_analysis 
            WHERE created_at >= NOW() - INTERVAL 24 HOUR
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        if not rows:
            print("📭 오늘 수집된 데이터가 없습니다. (분석 건너뜀)")
            return

        # 2. 프롬프트용 텍스트 구성
        reports_text = ""
        for idx, row in enumerate(rows):
            reports_text += f"""
            [분석 {idx+1}]
            - 출처: {row['source_name']} (점수: {row['sentiment_score']}점)
            - 제목: {row['title']}
            - 내용 요약: {row['analysis_content'][:300]}...
            --------------------------------
            """

        # 3. AI 프롬프트 (매수 1, 매도 1 선정 요청)
        prompt = f"""
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

        print(f"🤖 AI 분석 시작 (데이터 {len(rows)}건)...")
        client = Client(host='http://127.0.0.1:11434')
        
        # AI 호출
        response = client.chat(
            model='deepseek-r1:8b', 
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.1} 
        )
        
        raw_content = response['message']['content']
        print(f"📝 AI 원본 응답:\n{raw_content}")
        
        # 🚀 2. 정규식(Regex)을 이용한 무적의 JSON 추출기
        # 1) <think> 태그와 그 안의 내용 통째로 날려버리기
        clean_text = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL).strip()
        
        # 2) { 부터 } 까지의 실제 JSON 블록만 귀신같이 찾아내기
        match = re.search(r'\{.*\}', clean_text, flags=re.DOTALL)
        
        if not match:
            print("❌ 에러: AI 응답에서 JSON 괄호 '{ }' 를 찾을 수 없습니다.")
            return None
            
        json_str = match.group(0)
        
        try:
            result = json.loads(json_str)
            print("✅ JSON 파싱 완벽 성공!")
            # 정상 파싱되었으니 아래 DB 저장 로직으로 그대로 넘어갑니다.
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON 디코딩 에러: {e}")
            print(f"추출하려던 텍스트: {json_str}")
            return None
        
        # 5. DB 저장
        insert_query = """
            INSERT INTO daily_summary 
            (report_date, buy_stock, buy_ticker, buy_reason, sell_stock, sell_ticker, sell_reason)
            VALUES (CURDATE(), %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            result.get('buy_stock'), 
            result.get('buy_ticker', ''),
            result.get('buy_reason'), 
            result.get('sell_stock'), 
            result.get('sell_ticker', ''),
            result.get('sell_reason')
        ))
        conn.commit()
        
        print(f"✅ 리포트 생성 완료!")
        print(f"🐂 매수: {result['buy_stock']} ({result['buy_reason']})")
        print(f"🐻 매도: {result['sell_stock']} ({result['sell_reason']})")

        # 6. 텔레그램 알림
        send_telegram_alert(
            datetime.now().strftime("%Y-%m-%d"), 
            result['buy_stock'], result['buy_reason'], 
            result['sell_stock'], result['sell_reason']
        )

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        # 디버깅을 위해 원본 응답 출력
        if 'content' in locals():
            print("응답 원본:", content)

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    generate_daily_report()