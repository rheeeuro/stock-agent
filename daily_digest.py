import mysql.connector
import requests
import json
import sys
import os
from datetime import datetime
from ollama import Client

from dotenv import load_dotenv
load_dotenv()

# ==========================================
# [설정 1] 텔레그램 봇 정보 (본인 것으로 수정!)
# ==========================================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
CHAT_ID = os.getenv('CHAT_ID', '')

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
        data = {
            "chat_id": CHAT_ID, 
            "text": message, 
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        requests.post(url, data=data, timeout=10)
        print("📨 텔레그램 전송 완료")
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
            SELECT channel_name, video_title, analysis_content, sentiment_score 
            FROM video_analysis 
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
            - 채널: {row['channel_name']} (점수: {row['sentiment_score']}점)
            - 제목: {row['video_title']}
            - 내용 요약: {row['analysis_content'][:300]}...
            --------------------------------
            """

        # 3. AI 프롬프트 (매수 1, 매도 1 선정 요청)
        prompt = f"""
        너는 냉철한 '헤지펀드 매니저'야. 아래 수집된 주식 분석 리포트들을 종합해서 오늘의 투자 전략을 짜줘.

        [지시사항]
        1. **Top Pick (매수)**: 상승 여력이 가장 높거나 호재가 확실한 종목 1개 선정.
        2. **Short Pick (매도)**: 리스크가 크거나, 과열되었거나, 악재가 있는 종목 1개 선정. (없으면 '관망'이라고 적어)
        3. 선정 이유를 한 줄로 명확하게 요약해.

        [필수 출력 형식 - JSON Only]:
        {{
            "buy_stock": "종목명",
            "buy_reason": "선정 이유 요약",
            "sell_stock": "종목명",
            "sell_reason": "선정 이유 요약"
        }}

        [오늘의 리포트 데이터]:
        {reports_text}
        """

        print(f"🤖 AI 분석 시작 (데이터 {len(rows)}건)...")
        client = Client(host='http://127.0.0.1:11434')
        
        response = client.chat(model='deepseek-r1:8b', messages=[
            {'role': 'user', 'content': prompt}
        ])
        
        # 4. JSON 파싱 (DeepSeek <think> 태그 제거 로직 포함)
        content = response['message']['content']
        clean_json = content.replace('```json', '').replace('```', '').strip()
        if '</think>' in clean_json:
            clean_json = clean_json.split('</think>')[-1].strip()
            
        result = json.loads(clean_json)
        
        # 5. DB 저장
        insert_query = """
            INSERT INTO daily_summary 
            (report_date, buy_stock, buy_reason, sell_stock, sell_reason)
            VALUES (CURDATE(), %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            result['buy_stock'], result['buy_reason'], 
            result['sell_stock'], result['sell_reason']
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