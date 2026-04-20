"""갭상승 체크 워커 (평일 08:30)
전날 daily_stock_report Top 10의 '리포트 시각 → 현재가' 등락률을 CHAT_ID에게 전송
"""
import logging
from datetime import datetime

from core.logging_setup import setup_logging
from core.kiwoom_api import KiwoomConfig, KiwoomRestAPI
from core.trading_engine import AnalysisEngine
from core.repository.stock_report import (
    get_stock_report_dates,
    get_stock_reports_by_date,
)
from core.notifications import send_gap_check_alert

setup_logging()
logger = logging.getLogger("GapCheck")


def _most_recent_prior_date() -> str | None:
    dates = get_stock_report_dates(limit=5)
    today = datetime.now().date().isoformat()
    return next((d for d in dates if d < today), None)


def run():
    logger.info("=" * 60)
    logger.info("갭상승 체크 시작")
    logger.info("=" * 60)

    report_date = _most_recent_prior_date()
    if not report_date:
        logger.info("전날 리포트 없음 — 종료")
        return

    reports = get_stock_reports_by_date(report_date)[:10]
    if not reports:
        logger.info(f"{report_date} 리포트 데이터 없음 — 종료")
        return

    logger.info(f"{report_date} Top {len(reports)} 종목의 현재가 조회 중...")

    api = KiwoomRestAPI(KiwoomConfig())
    api.get_access_token()

    rows = []
    try:
        for r in reports:
            rank = r["rank_no"]
            name = r["stock_name"]
            code = r["stock_code"]
            report_price = int(r.get("current_price") or 0)
            try:
                info = api.get_stock_basic_info(code)
                now_price = abs(AnalysisEngine.parse_price(info.get("cur_prc", "0")))
                if report_price > 0 and now_price > 0:
                    pct = (now_price - report_price) / report_price * 100
                    rows.append({
                        "rank": rank, "name": name,
                        "report_price": report_price, "now_price": now_price,
                        "pct": pct,
                    })
                else:
                    rows.append({"rank": rank, "name": name, "error": True})
            except Exception as e:
                logger.error(f"{name}({code}) 조회 실패: {e}")
                rows.append({"rank": rank, "name": name, "error": True})
    finally:
        api.revoke_access_token()

    check_time = datetime.now().strftime("%m-%d %H:%M")
    send_gap_check_alert(report_date, check_time, rows)
    logger.info("갭상승 체크 완료")


if __name__ == "__main__":
    run()
