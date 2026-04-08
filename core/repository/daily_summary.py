"""일일 요약 리포트 데이터 접근"""
from datetime import date, datetime

from core.db import get_db


def save_daily_summary(buy_stock, buy_ticker, buy_reason, sell_stock, sell_ticker, sell_reason, market=None):
    """일일 요약 리포트 저장"""
    with get_db() as (conn, cursor):
        query = """
            INSERT INTO daily_summary
            (report_date, market, buy_stock, buy_ticker, buy_reason, sell_stock, sell_ticker, sell_reason)
            VALUES (CURDATE(), %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (market, buy_stock, buy_ticker, buy_reason, sell_stock, sell_ticker, sell_reason))
        conn.commit()


def get_latest_daily_summary(market: str | None = None) -> dict | None:
    """가장 최근 일일 요약 조회"""
    with get_db() as (conn, cursor):
        if market and market != "ALL":
            cursor.execute("""
                SELECT * FROM daily_summary WHERE market = %s
                ORDER BY report_date DESC, id DESC LIMIT 1
            """, (market,))
        else:
            cursor.execute("""
                SELECT * FROM daily_summary
                ORDER BY report_date DESC, id DESC LIMIT 1
            """)
        result = cursor.fetchone()
        if result and isinstance(result["report_date"], date):
            result["report_date"] = result["report_date"].isoformat()
        return result


def get_daily_summary_by_date(report_date: str) -> dict | None:
    """특정 날짜의 일일 요약 조회"""
    with get_db() as (conn, cursor):
        cursor.execute(
            "SELECT * FROM daily_summary WHERE report_date = %s LIMIT 1",
            (report_date,),
        )
        result = cursor.fetchone()
        if result and isinstance(result["report_date"], date):
            result["report_date"] = result["report_date"].isoformat()
        return result


def get_daily_summary_list(limit: int = 7, market: str | None = None) -> list[dict]:
    """최근 N건의 일일 요약 목록 조회"""
    with get_db() as (conn, cursor):
        if market and market != "ALL":
            cursor.execute(
                "SELECT * FROM daily_summary WHERE market = %s ORDER BY created_at DESC LIMIT %s",
                (market, limit),
            )
        else:
            cursor.execute(
                "SELECT * FROM daily_summary ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
        results = cursor.fetchall()
        for row in results:
            if isinstance(row["report_date"], (date, datetime)) or hasattr(row["report_date"], "isoformat"):
                row["report_date"] = str(row["report_date"]).split(" ")[0]
        return results
