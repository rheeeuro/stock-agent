import asyncio
from telethon import TelegramClient, events
from ollama import Client
import mysql.connector
import json
import requests
import os

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
        print(f"📋 감시 대상 채널 로드 완료: {len(channels)}개")
        return channels
    except Exception as e:
        print(f"❌ 채널 목록 로드 실패: {e}")
        return []

def save_to_db(channel, content, analysis, score, url):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        query = """
            INSERT INTO content_analysis 
            (external_id, source_name, title, analysis_content, sentiment_score, source_url, platform)
            VALUES (%s, %s, %s, %s, %s, %s, 'telegram')
        """
        cursor.execute(query, (url, channel, "텔레그램 속보", analysis, score, url))
        conn.commit()
        conn.close()
        print(f"✅ DB 저장 완료: {channel}")
    except Exception as e:
        print(f"❌ DB 에러: {e}")

def analyze_text(text):
    if len(text) < 30: return None, None # 너무 짧으면 무시

    prompt = f"""
    이 메시지가 '주식/경제/투자'와 직접 관련된 뉴스인지 판단해.
    관련 없으면 sentiment_score: -1 반환.
    
    [메시지]: {text[:2000]}
    
    [출력 형식 - JSON]:
    {{
        "sentiment_score": 75,
        "content": "3줄 요약..."
    }}
    """
    try:
        response = ai_client.chat(model='deepseek-r1:8b', messages=[{'role': 'user', 'content': prompt}])
        content = response['message']['content'].replace('```json', '').replace('```', '').strip()
        if '</think>' in content: content = content.split('</think>')[-1].strip()
        data = json.loads(content)
        
        if data.get('sentiment_score') == -1: return None, None
        return data['content'], data['sentiment_score']
    except:
        return None, None

# --- 메인 로직 시작 ---

# 1. DB에서 채널 목록 가져오기
target_chats = get_target_channels()

if not target_chats:
    print("⚠️ 감시할 채널이 없습니다. DB를 확인해주세요.")
    sys.exit()

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# 2. 가져온 채널 목록(target_chats)을 리스너에 등록
@client.on(events.NewMessage(chats=target_chats))
async def handler(event):
    chat = await event.get_chat()
    # 채널명 가져오기 (없으면 ID 사용)
    channel_name = chat.title if getattr(chat, 'title', None) else "Unknown"
    
    text = event.message.message
    msg_link = f"https://t.me/{chat.username}/{event.message.id}" if getattr(chat, 'username', None) else ""

    print(f"📩 [{channel_name}] 새 메시지 도착")
    
    analysis, score = analyze_text(text)
    
    if analysis:
        save_to_db(channel_name, text, analysis, score, msg_link)

print(f"🚀 텔레그램 감시 시작 (대상 {len(target_chats)}개)...")
client.start()
client.run_until_disconnected()