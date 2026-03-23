import asyncio
import os
import logging
import sys
import time

from telethon import TelegramClient, events

from core.logging_setup import setup_logging
from core.config import TELEGRAM_API_ID, TELEGRAM_API_HASH
from core.prompts import TELEGRAM_ANALYSIS_PROMPT
from core.ai_service import analyze_content
from core.repository import get_active_sources, save_content_analysis
from core.filters import should_save_content
from core.notifications import send_analysis_alert
from core.ticker import get_tickers_by_market

setup_logging()


# 특정 에러 발생 시 자동 재시작 트리거 (Telethon 세션/보안 에러 대응)
class SuicideOnOldMessageFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        if "Server sent a very old message" in msg or "Too many messages had to be ignored consecutively" in msg:
            print(f"\n🚨 [치명적 에러 감지] {msg}", flush=True)
            print("🚨 Telethon 세션/보안 에러 발생! PM2를 통한 깨끗한 재시작을 위해 강제 종료합니다...", flush=True)
            os._exit(1)
        return True


if logging.root.handlers:
    for handler in logging.root.handlers:
        handler.addFilter(SuicideOnOldMessageFilter())
else:
    logging.getLogger().addFilter(SuicideOnOldMessageFilter())


SESSION_NAME = 'stock_session'
MIN_TEXT_LENGTH = 30


def get_target_channels():
    """DB에서 감시할 텔레그램 채널 목록을 가져와 ID 타입 변환"""
    try:
        rows = get_active_sources('telegram')
        channels = []
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

            if len(text) < MIN_TEXT_LENGTH:
                logging.info(f"⏭️ [스킵] 메시지가 너무 짧음 ({len(text)}자 < {MIN_TEXT_LENGTH}자)")
                return

            prompt = TELEGRAM_ANALYSIS_PROMPT.format(text=text)
            result = analyze_content(prompt)

            if not result:
                logging.info(f"⏭️ [{channel_name}] 분석 결과 없음 - 저장하지 않습니다.")
                return

            tickers = get_tickers_by_market(result.related_companies, result.market) if hasattr(result, 'related_companies') and result.related_companies else []

            if not should_save_content(result.sentiment_score, tickers, skip_neutral=True, allow_no_ticker=True):
                return

            save_content_analysis(
                external_id=msg_link,
                source_name=channel_name,
                title=result.title,
                content=result.content,
                score=result.sentiment_score,
                source_url=msg_link,
                related_tickers=tickers,
                platform='telegram',
                market=result.market,
            )

            # 30~80점 구간은 텔레그램 알림 생략
            if result.sentiment_score is not None and 30 <= result.sentiment_score <= 80:
                logging.info(f"⏭️ [알림 스킵] 점수 {result.sentiment_score}점(30~80 구간)으로 텔레그램 전송 생략")
            else:
                send_analysis_alert(channel_name, result.title, result.content, result.sentiment_score, tickers, result.market)

        client.start()
        logging.info("✅ 텔레그램 서버 연결 성공! 메시지 감시를 시작합니다.")
        client.run_until_disconnected()

    except Exception as e:
        logging.error(f"💥 텔레그램 연결 끊김 또는 에러 발생: {e}")
        logging.info("⏳ 10초 후 서버에 자동 재접속을 시도합니다...")
        time.sleep(10)
