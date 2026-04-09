"""종목일간리포트 데이터 접근"""
import json
from datetime import date, datetime

from core.db import get_db


def save_stock_reports(candidates: list[dict]):
    """Phase 2 결과를 일괄 저장 (오늘 날짜 기존 데이터 삭제 후 INSERT)"""
    if not candidates:
        return

    with get_db() as (conn, cursor):
        cursor.execute("DELETE FROM daily_stock_report WHERE report_date = CURDATE()")

        query = """
            INSERT INTO daily_stock_report
            (report_date, stock_code, stock_name, sector, current_price, change_pct,
             trading_value, market_cap, supply_grade, inst_net_buy, frgn_net_buy,
             indv_net_buy, prog_net_buy, supply_days, supply_history, ma_aligned, near_high,
             is_leader, score, rank_no)
            VALUES (CURDATE(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        for c in candidates:
            supply_history_json = json.dumps(
                c.get("supply_history", []), ensure_ascii=False
            ) if c.get("supply_history") else None
            cursor.execute(query, (
                c["stock_code"], c["stock_name"], c["sector"],
                c["current_price"], c["change_pct"],
                c["trading_value"], c["market_cap"],
                c["supply_grade"], c["inst_net_buy"], c["frgn_net_buy"],
                c["indv_net_buy"], c["prog_net_buy"], c["supply_days"],
                supply_history_json,
                c["ma_aligned"], c["near_high"],
                c["is_leader"], c["score"], c["rank_no"],
            ))
        conn.commit()


def get_stock_report(report_date: str, stock_code: str) -> dict | None:
    """특정 날짜 + 종목 리포트 조회"""
    with get_db() as (conn, cursor):
        cursor.execute(
            "SELECT * FROM daily_stock_report WHERE report_date = %s AND stock_code = %s",
            (report_date, stock_code),
        )
        result = cursor.fetchone()
        if result:
            _serialize_dates(result)
        return result


def get_stock_report_history(stock_code: str, days: int = 3) -> list[dict]:
    """특정 종목의 최근 N일 리포트 조회 (수급 동향용)"""
    with get_db() as (conn, cursor):
        cursor.execute(
            """SELECT * FROM daily_stock_report
               WHERE stock_code = %s
               ORDER BY report_date DESC
               LIMIT %s""",
            (stock_code, days),
        )
        results = cursor.fetchall()
        for row in results:
            _serialize_dates(row)
        return results


def get_stock_reports_by_date(report_date: str) -> list[dict]:
    """특정 날짜의 전체 종목 리포트 목록 (점수순)"""
    with get_db() as (conn, cursor):
        cursor.execute(
            """SELECT * FROM daily_stock_report
               WHERE report_date = %s
               ORDER BY rank_no ASC""",
            (report_date,),
        )
        results = cursor.fetchall()
        for row in results:
            _serialize_dates(row)
        return results


def get_stock_report_dates(limit: int = 30) -> list[str]:
    """리포트가 존재하는 날짜 목록"""
    with get_db() as (conn, cursor):
        cursor.execute(
            """SELECT DISTINCT report_date
               FROM daily_stock_report
               ORDER BY report_date DESC
               LIMIT %s""",
            (limit,),
        )
        results = cursor.fetchall()
        return [
            row["report_date"].isoformat()
            if isinstance(row["report_date"], (date, datetime))
            else str(row["report_date"])
            for row in results
        ]


def _serialize_dates(row: dict):
    """날짜 필드 직렬화"""
    if isinstance(row.get("report_date"), (date, datetime)):
        row["report_date"] = row["report_date"].isoformat().split("T")[0]
    if isinstance(row.get("created_at"), datetime):
        row["created_at"] = row["created_at"].isoformat()
    # boolean 변환 (MariaDB TINYINT → Python bool)
    for key in ("ma_aligned", "near_high", "is_leader"):
        if key in row:
            row[key] = bool(row[key])
    # supply_history JSON 파싱
    if "supply_history" in row and isinstance(row["supply_history"], str):
        row["supply_history"] = json.loads(row["supply_history"])
    if row.get("supply_history") is None:
        row["supply_history"] = []
