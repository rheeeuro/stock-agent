import sys
import logging
from datetime import datetime
from ollama import Client

from core.config import OLLAMA_HOST
from core.db import get_db
from core.prompts import DAILY_DIGEST_PROMPT
from core.ai_utils import parse_ai_json
from core.notifications import send_daily_digest_alert

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)


def generate_daily_report():
    try:
        with get_db() as (conn, cursor):
            # 1. 오늘(최근 24시간) 수집된 데이터 조회
            logging.info("🔍 오늘의 데이터 조회 중...")
            query = """
                SELECT source_name, title, analysis_content, sentiment_score 
                FROM content_analysis 
                WHERE created_at >= NOW() - INTERVAL 24 HOUR
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            if not rows:
                logging.info("📭 오늘 수집된 데이터가 없습니다. (분석 건너뜀)")
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

            # 3. AI 프롬프트
            prompt = DAILY_DIGEST_PROMPT.format(reports_text=reports_text)

            logging.info(f"🤖 AI 분석 시작 (데이터 {len(rows)}건)...")
            client = Client(host=OLLAMA_HOST)
            
            response = client.chat(
                model='deepseek-r1:8b', 
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.1} 
            )
            
            raw_content = response['message']['content']
            logging.info(f"📝 AI 원본 응답:\n{raw_content}")
            
            # 4. AI 응답 파싱 (공통 유틸 사용)
            result = parse_ai_json(raw_content)
            
            if result is None:
                logging.error("❌ AI 응답에서 JSON을 파싱할 수 없습니다.")
                return
            
            logging.info("✅ JSON 파싱 완벽 성공!")
            
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
            
            logging.info(f"✅ 리포트 생성 완료!")
            logging.info(f"🐂 매수: {result['buy_stock']} ({result['buy_reason']})")
            logging.info(f"🐻 매도: {result['sell_stock']} ({result['sell_reason']})")

            # 6. 텔레그램 알림
            send_daily_digest_alert(
                datetime.now().strftime("%Y-%m-%d"), 
                result['buy_stock'], result['buy_reason'], 
                result['sell_stock'], result['sell_reason']
            )

    except Exception as e:
        logging.error(f"❌ 에러 발생: {e}")
        if 'raw_content' in locals():
            logging.error(f"응답 원본: {raw_content}")


if __name__ == "__main__":
    generate_daily_report()