"""
알림 모듈 - 텔레그램 메시지 전송 로직 통합
"""
import logging
import requests
from core.config import TELEGRAM_TOKEN, CHAT_ID, CHAT_ID2


def _get_chat_ids() -> list:
    """유효한 CHAT_ID 목록 반환"""
    return [cid for cid in [CHAT_ID, CHAT_ID2] if cid]


def _send_telegram_message(message: str):
    """텔레그램 메시지 전송 (내부 공통 로직)"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    chat_ids = _get_chat_ids()
    for chat_id in chat_ids:
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        requests.post(url, data=data, timeout=10)
    return len(chat_ids)


def send_analysis_alert(channel: str, title: str, analysis: str, score: int = 50, related_tickers: list[dict] | None = None, market=None):
    """콘텐츠 분석 결과 텔레그램 전송 (YouTube/Telegram 공통)"""
    try:
        if score >= 80:
            status = "🔥 *강력 매수* (탐욕)"
        elif score >= 60:
            status = "📈 *긍정적* (매수)"
        elif score <= 20:
            status = "🥶 *공포* (현금화)"
        elif score <= 40:
            status = "📉 *부정적* (보수적)"
        else:
            status = "😐 *중립* (관망)"

        short_analysis = analysis[:800] + "..." if len(analysis) > 800 else analysis

        ticker_display = ", ".join(
            f"{t['name']}({t['ticker']})" for t in (related_tickers or [])
        )

        formatted_analysis = short_analysis.replace("**", "*")
        message = (
            f"🚨 *[{channel}] 분석 완료!*\n"
            f"📊 관점: {score}점 - {status}\n\n"
            f"📺 {title}\n"
            f"관련 종목: {ticker_display}\n"
            f"시장: {market}\n"
            f"──────────────────\n"
            f"{formatted_analysis}\n\n"
            f"👉 [대시보드 바로가기](https://stock.rheeeuro.com)"
        )

        count = _send_telegram_message(message)
        logging.info(f"📨 텔레그램 전송 성공: [{market}] {title} ({score}점) -> {count}개 채팅방")

    except Exception as e:
        logging.error(f"❌ 텔레그램 에러: {e}")


def send_daily_digest_alert(date: str, buy: str, buy_reason: str, sell: str, sell_reason: str):
    """일일 요약 리포트 텔레그램 전송"""
    try:
        message = (
            f"📅 *[{date}] 오늘의 AI 투자 전략*\n\n"
            f"🐂 *매수(Buy): {buy}*\n"
            f"└ {buy_reason}\n\n"
            f"🐻 *매도(Sell): {sell}*\n"
            f"└ {sell_reason}\n\n"
            f"👉 [대시보드 확인하기](https://stock.rheeeuro.com)"
        )

        count = _send_telegram_message(message)
        logging.info(f"📨 텔레그램 전송 완료 -> {count}개 채팅방")

    except Exception as e:
        logging.error(f"❌ 텔레그램 전송 실패: {e}")
