import asyncio
from telethon import TelegramClient, events
from ollama import Client
import mysql.connector
import json
import requests
import os
import logging
import sys

# 로깅 설정: 시간 포함
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)

from dotenv import load_dotenv
load_dotenv()

# ==========================================
# [설정 1] 텔레그램 API 정보 (my.telegram.org)
# ==========================================
API_ID = os.getenv('TELEGRAM_API_ID')       # 예: 1234567
API_HASH = os.getenv('TELEGRAM_API_HASH') # 예: 'a1b2c3...'
SESSION_NAME = 'stock_session'      # 세션 파일 이름 (자동 생성됨)

# DB 및 기타 설정 (기존과 동일)
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
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')


# AI 클라이언트
ai_client = Client(host='http://127.0.0.1:11434')

def get_target_channels():
    """DB에서 감시할 채널 목록을 가져옴"""
    channels = []
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        # 활성화된 채널만 조회 (sources 테이블 사용)
        cursor.execute("SELECT identifier FROM sources WHERE platform = 'telegram' AND is_active = TRUE")
        rows = cursor.fetchall()
        
        for row in rows:
            ident = row['identifier']
            # 숫자로 된 ID(예: -100123...)는 정수형(int)으로 변환해야 텔레톤이 인식함
            if ident.startswith('-') or ident.isdigit():
                channels.append(int(ident))
            else:
                channels.append(ident) # username은 문자열 그대로
                
        conn.close()
        logging.info(f"📋 감시 대상 채널 로드 완료: {len(channels)}개")
        return channels
    except Exception as e:
        logging.error(f"❌ 채널 목록 로드 실패: {e}")
        return []

def save_to_db(channel, title, content, analysis, score, url, related_tickers):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        tickers_json_str = json.dumps(related_tickers)
        query = """
            INSERT INTO content_analysis 
            (external_id, source_name, title, analysis_content, sentiment_score, source_url, related_tickers, platform)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'telegram')
        """
        cursor.execute(query, (url, channel, title, analysis, score, url, tickers_json_str))
        conn.commit()
        conn.close()
        logging.info(f"✅ DB 저장 완료: {channel}")
    except Exception as e:
        logging.error(f"❌ DB 에러: {e}")

def analyze_text(text):
    if len(text) < 30: return None, None, None, None # 너무 짧으면 무시

    prompt = f"""
        [중요 지시사항]
        먼저 이 메시지가 **'주식, 경제, 투자, 기업 분석, 시장 전망'**과 관련된 내용인지 판단해.
        
        1. 만약 **관련 없는 내용(일상, 먹방, 게임, 단순 유머 등)**이라면:
           반드시 JSON의 sentiment_score를 **-1**로 설정하고 content는 비워둬.
           
        2. **관련 있는 내용**이라면 다음 두 가지를 분석해서 반드시 **JSON 포맷**으로만 출력해.
            - sentiment_score: 시장 전망 점수 (0: 폭락/공포 ~ 50: 중립 ~ 100: 폭등/탐욕)
            - content: 마크다운 형식의 투자 인사이트 분석 리포트 (3줄 요약, 종목, 대응 전략 포함)
            - title: 제목
            - related_tickers: 텍스트에서 언급된 주식 종목이 있다면, 반드시 영문 티커(Ticker) 심볼로 변환하여 리스트 형태로 추출할 것. (예: ["NVDA", "TSLA", "005930.KS"]). 없으면 빈 리스트 [] 를 반환할 것.
                - 🚨주의: 반드시 '현재 주식 시장에 상장된 공식 기업'의 티커만 추출해라. Grok, OpenAI, ChatGPT 같은 제품명, AI 모델, 비상장 기업은 절대 포함하지 마라!
        
            [content는 반드시 아래 Markdown 형식을 지켜서 출력해]:
            
                ## 1. 3줄 핵심 요약
                - (요약 1)
                - (요약 2)  
                - (요약 3)
                
                ## 2. 주요 언급 종목
                - **종목명**: (호재/악재 판단)
                
                ## 3. 대응 전략
                > (한 줄 조언)
        
        [필수 출력 형식 - JSON Only]:
        {{
            "sentiment_score": 75,  // 아닐 경우 -1
            "content": "분석 내용..." // 아닐 경우 ""
            "title": "제목",
            "related_tickers": ["추출된", "티커", "목록"] // 아닐 경우 []
        }}

        [메시지 내용]: {text}
    """
    try:
        response = ai_client.chat(model='deepseek-r1:8b', messages=[{'role': 'user', 'content': prompt}])
        content = response['message']['content'].replace('```json', '').replace('```', '').strip()
        if '</think>' in content: content = content.split('</think>')[-1].strip()
        data = json.loads(content)
        
        if data.get('sentiment_score') == -1: return None, None, None, None
        return data['title'], data['content'], data['sentiment_score'], data['related_tickers']
    except:
        return None, None, None, None

# --- 메인 로직 시작 ---

# 1. DB에서 채널 목록 가져오기
target_chats = get_target_channels()

if not target_chats:
    logging.warning("⚠️ 감시할 채널이 없습니다. DB를 확인해주세요.")
    sys.exit()

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# 2. 가져온 채널 목록(target_chats)을 리스너에 등록
@client.on(events.NewMessage(chats=target_chats))
async def handler(event):
    chat = await event.get_chat()
    # 채널명 가져오기 (없으면 ID 사용)
    channel_name = chat.title if getattr(chat, 'title', None) else "Unknown"
    
    text = event.message.message
    username = getattr(chat, 'username', None)
    if username:
        msg_link = f"https://t.me/{username}/{event.message.id}"
    else:
        # 비공개 채널/그룹 처리 (ID 활용)
        cid = str(chat.id)
        if cid.startswith('-100'):
            cid = cid[4:]
        msg_link = f"https://t.me/c/{cid}/{event.message.id}"

    logging.info(f"📩 [{channel_name}] 새 메시지 도착")
    
    title, analysis, score, related_tickers = analyze_text(text)
    
    if analysis:
        save_to_db(channel_name, title, text, analysis, score, msg_link, related_tickers)

logging.info(f"🚀 텔레그램 감시 시작 (대상 {len(target_chats)}개)...")
client.start()
client.run_until_disconnected()