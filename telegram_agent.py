import asyncio
from telethon import TelegramClient, events
from ollama import Client
import mysql.connector
import json
import os
import logging
import sys
import time

# 로깅 설정: 시간 포함
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)

# ==========================================
# 🚀 특정 에러 발생 시 자동 자폭(재시작) 트리거
# ==========================================
class SuicideOnOldMessageFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        # Telethon 보안 에러 및 세션 꼬임 감지
        if "Server sent a very old message" in msg or "Too many messages had to be ignored consecutively" in msg:
            print(f"\n🚨 [치명적 에러 감지] {msg}", flush=True)
            print("🚨 Telethon 세션/보안 에러 발생! PM2를 통한 깨끗한 재시작을 위해 강제 종료합니다...", flush=True)
            os._exit(1)
        return True

# 루트 로거의 모든 핸들러에 필터 추가 (자식 로거의 메시지도 모두 잡기 위해)
if logging.root.handlers:
    for handler in logging.root.handlers:
        handler.addFilter(SuicideOnOldMessageFilter())
else:
    logging.getLogger().addFilter(SuicideOnOldMessageFilter())

from core.config import DB_CONFIG, TELEGRAM_API_ID, TELEGRAM_API_HASH, OLLAMA_HOST, OLLAMA_MODEL
from core.db import get_db
from core.prompts import TELEGRAM_ANALYSIS_PROMPT
from core.ai_utils import parse_ai_json

SESSION_NAME = 'stock_session'

# AI 클라이언트
ai_client = Client(host=OLLAMA_HOST)

def get_target_channels():
    """DB에서 감시할 채널 목록을 가져옴"""
    channels = []
    try:
        with get_db() as (conn, cursor):
            cursor.execute("SELECT identifier FROM sources WHERE platform = 'telegram' AND is_active = TRUE")
            rows = cursor.fetchall()
            
            for row in rows:
                ident = row['identifier']
                if ident.startswith('-') or ident.isdigit():
                    channels.append(int(ident))
                else:
                    channels.append(ident)
                    
        logging.info(f"📋 감시 대상 채널 로드 완료: {len(channels)}개")
        return channels
    except Exception as e:
        logging.error(f"❌ 채널 목록 로드 실패: {e}")
        return []

def save_to_db(channel, title, content, analysis, score, url, related_tickers, market):
    try:
        with get_db() as (conn, cursor):
            tickers_json_str = json.dumps(related_tickers)
            query = """
                INSERT INTO content_analysis 
                (external_id, source_name, title, analysis_content, sentiment_score, source_url, related_tickers, platform, market)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'telegram', %s)
            """
            cursor.execute(query, (url, channel, title, analysis, score, url, tickers_json_str, market))
            conn.commit()
        logging.info(f"✅ DB 저장 완료: [{market}] {title} (점수: {score}, 티커: {related_tickers})")
    except Exception as e:
        logging.error(f"❌ DB 에러: {e}")

def analyze_text(text):
    if len(text) < 30: return None, None, None, None, None

    prompt = TELEGRAM_ANALYSIS_PROMPT.format(text=text)
    try:
        response = ai_client.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}])
        data = parse_ai_json(response['message']['content'])
        
        if data is None:
            return None, None, None, None, None
        
        if data.get('sentiment_score') == -1:
            return None, None, None, None, None
            
        return data['title'], data['content'], data['sentiment_score'], data['related_tickers'], data['market']
    except Exception as e:
        logging.error(f"AI 분석 에러: {e}")
        return None, None, None, None, None




while True:
    try:
        logging.info("🔄 텔레그램 클라이언트 메모리 초기화 및 접속 시도...")
        client = TelegramClient(SESSION_NAME, TELEGRAM_API_ID, TELEGRAM_API_HASH)

        target_chats = get_target_channels()

        if not target_chats:
            logging.warning("⚠️ 감시할 채널이 없습니다. DB를 확인해주세요.")
            sys.exit()

        logging.info(f"🚀 텔레그램 감시 시작 (대상 {len(target_chats)}개)...")

        @client.on(events.NewMessage(chats=target_chats))   
        async def handler(event):
            chat = await event.get_chat()
            channel_name = chat.title if getattr(chat, 'title', None) else "Unknown"
            
            text = event.message.message
            if not text:
                return

            username = getattr(chat, 'username', None)
            if username:
                msg_link = f"https://t.me/{username}/{event.message.id}"
            else:
                cid = str(chat.id)
                if cid.startswith('-100'):
                    cid = cid[4:]
                msg_link = f"https://t.me/c/{cid}/{event.message.id}"

            logging.info(f"📩 [{channel_name}] 새 메시지 도착")
            
            title, analysis, score, related_tickers, market = analyze_text(text)
            
            if analysis:
                # 🚀 필터 1: 관련 티커가 없으면 스킵
                if not related_tickers or len(related_tickers) == 0:
                    logging.info(f"⏭️ [스킵] 구체적인 티커(Ticker)가 없어 저장하지 않습니다.")
                    return

                # 🚀 필터 2: 점수가 40점 ~ 70점 사이(중립)면 스킵
                if score is not None and 40 <= score <= 70:
                    logging.info(f"⏭️ [스킵] 점수가 {score}점(40~70 구간)이라 저장하지 않습니다.")
                    return
                    
                save_to_db(channel_name, title, text, analysis, score, msg_link, related_tickers, market)

        client.start()
        logging.info("✅ 텔레그램 서버 연결 성공! 메시지 감시를 시작합니다.")
        client.run_until_disconnected() 
        
    except Exception as e:
        logging.error(f"💥 텔레그램 연결 끊김 또는 에러 발생: {e}")
        logging.info("⏳ 10초 후 서버에 자동 재접속을 시도합니다...")
        time.sleep(10)