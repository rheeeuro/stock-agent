"""
데이터 접근 모듈 - 모든 DB CRUD 작업을 한 곳에서 관리
"""
import json
import math
import logging
from datetime import date, datetime

from core.db import get_db
from core.ai_utils import remove_markdown_code_blocks


# ── 공통 (에이전트 + API) ──

def get_active_sources(platform: str) -> list[dict]:
    """활성화된 소스 목록 조회 (telegram / youtube)"""
    with get_db() as (conn, cursor):
        cursor.execute(
            "SELECT identifier, name FROM sources WHERE platform = %s AND is_active = TRUE",
            (platform,),
        )
        return cursor.fetchall()


def is_content_processed(external_id: str) -> bool:
    """이미 처리된 콘텐츠인지 확인"""
    with get_db() as (conn, cursor):
        cursor.execute(
            "SELECT count(*) as cnt FROM content_analysis WHERE external_id = %s",
            (external_id,),
        )
        return cursor.fetchone()["cnt"] > 0


def save_content_analysis(
    external_id: str,
    source_name: str,
    title: str,
    content: str,
    score: int,
    source_url: str,
    related_tickers: list,
    platform: str,
    market: str,
):
    """콘텐츠 분석 결과 저장 (telegram / youtube 공통)"""
    content = remove_markdown_code_blocks(content)
    with get_db() as (conn, cursor):
        query = """
            INSERT INTO content_analysis
            (external_id, source_name, title, analysis_content, sentiment_score,
             source_url, related_tickers, platform, market)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            external_id, source_name, title, content, score,
            source_url, json.dumps(related_tickers), platform, market,
        ))
        conn.commit()
    logging.info(f"✅ DB 저장 완료: [{market}] {title} (점수: {score}, 티커: {related_tickers})")


def save_daily_summary(buy_stock, buy_ticker, buy_reason, sell_stock, sell_ticker, sell_reason):
    """일일 요약 리포트 저장"""
    with get_db() as (conn, cursor):
        query = """
            INSERT INTO daily_summary
            (report_date, buy_stock, buy_ticker, buy_reason, sell_stock, sell_ticker, sell_reason)
            VALUES (CURDATE(), %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (buy_stock, buy_ticker, buy_reason, sell_stock, sell_ticker, sell_reason))
        conn.commit()


def get_recent_analyses(hours: int = 24, market: str | None = None) -> list[dict]:
    """최근 N시간 내 수집된 분석 데이터 조회 (일일 요약용). market='US'|'KR'로 필터 가능"""
    with get_db() as (conn, cursor):
        query = """
            SELECT source_name, title, analysis_content, sentiment_score
            FROM content_analysis
            WHERE created_at >= NOW() - INTERVAL %s HOUR
        """
        params: list = [hours]

        if market in ("US", "KR"):
            query += " AND market = %s"
            params.append(market)

        cursor.execute(query, tuple(params))
        return cursor.fetchall()


# ── API 전용 ──

def get_contents_paginated(page: int = 1, limit: int = 12, market: str = "ALL") -> dict:
    """페이지네이션된 콘텐츠 목록 조회"""
    with get_db() as (conn, cursor):
        offset = (page - 1) * limit

        where_clause = "WHERE created_at >= NOW() - INTERVAL 7 DAY"
        params: list = []

        if market in ("US", "KR"):
            where_clause += " AND market = %s"
            params.append(market)

        cursor.execute(
            f"SELECT COUNT(*) as total_count FROM content_analysis {where_clause}",
            tuple(params),
        )
        total_count = cursor.fetchone()["total_count"]

        cursor.execute(
            f"""
            SELECT id, external_id, source_name, title,
                   analysis_content, sentiment_score,
                   platform, market, source_url, created_at
            FROM content_analysis {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset]),
        )
        result = cursor.fetchall()

        for row in result:
            if row["created_at"]:
                row["created_at"] = str(row["created_at"])
            if row["sentiment_score"] is None:
                row["sentiment_score"] = 50

        total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

        return {
            "data": result,
            "pagination": {
                "current_page": page,
                "limit": limit,
                "total_items": total_count,
                "total_pages": total_pages,
                "has_next_page": page < total_pages,
                "has_prev_page": page > 1,
            },
        }


def get_youtube_sources() -> list[dict]:
    """YouTube 소스 전체 조회"""
    with get_db() as (conn, cursor):
        cursor.execute("SELECT * FROM sources WHERE platform = 'youtube'")
        return cursor.fetchall()


def get_latest_daily_summary() -> dict | None:
    """가장 최근 일일 요약 조회"""
    with get_db() as (conn, cursor):
        cursor.execute("""
            SELECT * FROM daily_summary
            ORDER BY report_date DESC, id DESC
            LIMIT 1
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


def get_daily_summary_list(limit: int = 7) -> list[dict]:
    """최근 N건의 일일 요약 목록 조회"""
    with get_db() as (conn, cursor):
        cursor.execute(
            "SELECT * FROM daily_summary ORDER BY created_at DESC LIMIT %s",
            (limit,),
        )
        results = cursor.fetchall()
        for row in results:
            if isinstance(row["report_date"], (date, datetime)) or hasattr(row["report_date"], "isoformat"):
                row["report_date"] = str(row["report_date"]).split(" ")[0]
        return results


def get_contents_by_ticker(ticker: str) -> list[dict]:
    """특정 티커 관련 콘텐츠 조회"""
    with get_db() as (conn, cursor):
        cursor.execute(
            """
            SELECT * FROM content_analysis
            WHERE created_at >= NOW() - INTERVAL 7 DAY
              AND related_tickers LIKE %s
            ORDER BY created_at DESC
            """,
            (f"%{ticker}%",),
        )
        results = cursor.fetchall()
        for row in results:
            if isinstance(row["created_at"], datetime):
                row["created_at"] = row["created_at"].isoformat()
        return results


def get_stock_name_from_db(ticker: str) -> str:
    """DB에서 티커의 종목명 조회"""
    with get_db() as (conn, cursor):
        cursor.execute(
            """
            SELECT buy_stock AS stock_name FROM daily_summary WHERE buy_ticker = %s
            UNION
            SELECT sell_stock AS stock_name FROM daily_summary WHERE sell_ticker = %s
            LIMIT 1
            """,
            (ticker, ticker),
        )
        result = cursor.fetchone()
        if result and result["stock_name"]:
            return result["stock_name"]
        return ticker
