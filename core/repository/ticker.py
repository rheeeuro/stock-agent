"""티커 사전 데이터 접근"""
from datetime import datetime

from core.db import get_db


def lookup_ticker(company_name: str) -> dict | None:
    """ticker_dictionary에서 기업명으로 티커 조회 (ACTIVE 우선, PENDING도 허용)"""
    with get_db() as (conn, cursor):
        cursor.execute(
            """
            SELECT id, company_name, ticker_symbol, status
            FROM ticker_dictionary
            WHERE company_name = %s
            ORDER BY FIELD(status, 'ACTIVE', 'PENDING', 'INACTIVE')
            LIMIT 1
            """,
            (company_name,),
        )
        return cursor.fetchone()


def lookup_name_by_ticker(ticker_symbol: str) -> str | None:
    """ticker_dictionary에서 티커 심볼로 기업명 조회 (ACTIVE 우선)"""
    with get_db() as (conn, cursor):
        cursor.execute(
            """
            SELECT company_name FROM ticker_dictionary
            WHERE ticker_symbol = %s AND status != 'INACTIVE'
            ORDER BY FIELD(status, 'ACTIVE', 'PENDING')
            LIMIT 1
            """,
            (ticker_symbol,),
        )
        row = cursor.fetchone()
        return row["company_name"] if row else None


def save_ticker(company_name: str, ticker_symbol: str, market: str = "KR", status: str = "PENDING") -> None:
    """ticker_dictionary에 새 항목 추가 (중복이면 무시)"""
    with get_db() as (conn, cursor):
        cursor.execute(
            """
            INSERT IGNORE INTO ticker_dictionary (company_name, ticker_symbol, market, status)
            VALUES (%s, %s, %s, %s)
            """,
            (company_name, ticker_symbol, market.upper(), status),
        )
        conn.commit()


def get_ticker_dictionary(status: str | None = None, market: str | None = None) -> list[dict]:
    """ticker_dictionary 전체 조회. status, market 필터 가능"""
    with get_db() as (conn, cursor):
        conditions: list[str] = []
        params: list[str] = []
        if status:
            conditions.append("status = %s")
            params.append(status)
        if market:
            conditions.append("market = %s")
            params.append(market.upper())

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        order = "updated_at DESC" if conditions else "FIELD(status, 'PENDING', 'ACTIVE', 'INACTIVE'), updated_at DESC"
        cursor.execute(f"SELECT * FROM ticker_dictionary{where} ORDER BY {order}", params)

        results = cursor.fetchall()
        for row in results:
            for col in ("created_at", "updated_at"):
                if isinstance(row.get(col), datetime):
                    row[col] = row[col].isoformat()
        return results


def update_ticker(ticker_id: int, company_name: str, ticker_symbol: str, market: str, status: str) -> bool:
    """ticker_dictionary 항목 수정"""
    with get_db() as (conn, cursor):
        cursor.execute(
            """
            UPDATE ticker_dictionary
            SET company_name = %s, ticker_symbol = %s, market = %s, status = %s
            WHERE id = %s
            """,
            (company_name, ticker_symbol, market.upper(), status, ticker_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_ticker(ticker_id: int) -> bool:
    """ticker_dictionary 항목 삭제"""
    with get_db() as (conn, cursor):
        cursor.execute("DELETE FROM ticker_dictionary WHERE id = %s", (ticker_id,))
        conn.commit()
        return cursor.rowcount > 0
