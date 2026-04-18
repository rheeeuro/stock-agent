"""콘텐츠 분석 데이터 접근"""
import json
import math
import logging
from datetime import datetime

from core.db import get_db
from core.ai_utils import remove_markdown_code_blocks


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
                   platform, market, source_url, created_at, related_tickers
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
            if row.get("related_tickers"):
                try:
                    row["related_tickers"] = json.loads(row["related_tickers"])
                except Exception:
                    row["related_tickers"] = []
            else:
                row["related_tickers"] = []

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
    logging.info(f"DB 저장 완료: [{market}] {title} (점수: {score}, 티커: {related_tickers})")


def get_today_content_by_stock(stock_code: str) -> list[dict]:
    """오늘 날짜의 특정 종목 관련 콘텐츠 분석 조회 (ticker로 매칭)"""
    code_part = stock_code.split(".")[0]
    with get_db() as (conn, cursor):
        cursor.execute(
            """
            SELECT id, title, analysis_content, sentiment_score,
                   source_name, platform, source_url, created_at
            FROM content_analysis
            WHERE DATE(created_at) = CURDATE()
              AND market = 'KR'
              AND related_tickers LIKE %s
            ORDER BY created_at DESC
            """,
            (f"%{code_part}%",),
        )
        results = cursor.fetchall()
        for row in results:
            if isinstance(row["created_at"], datetime):
                row["created_at"] = row["created_at"].isoformat()
            if row["sentiment_score"] is None:
                row["sentiment_score"] = 50
        return results


def get_content_by_stock_and_date(
    stock_code: str, report_date: str
) -> list[dict]:
    """특정 날짜의 특정 종목 관련 콘텐츠 분석 조회 (ticker로 매칭)"""
    code_part = stock_code.split(".")[0]
    with get_db() as (conn, cursor):
        cursor.execute(
            """
            SELECT id, title, analysis_content, sentiment_score,
                   source_name, platform, source_url, created_at
            FROM content_analysis
            WHERE DATE(created_at) = %s
              AND market = 'KR'
              AND related_tickers LIKE %s
            ORDER BY created_at DESC
            """,
            (report_date, f"%{code_part}%"),
        )
        results = cursor.fetchall()
        for row in results:
            if isinstance(row["created_at"], datetime):
                row["created_at"] = row["created_at"].isoformat()
            if row["sentiment_score"] is None:
                row["sentiment_score"] = 50
        return results


def get_recent_analyses(hours: int = 24, market: str | None = None) -> list[dict]:
    """최근 N시간 내 수집된 분석 데이터 조회 (일일 요약용)"""
    with get_db() as (conn, cursor):
        query = """
            SELECT source_name, title, analysis_content, sentiment_score, related_tickers
            FROM content_analysis
            WHERE created_at >= NOW() - INTERVAL %s HOUR
        """
        params: list = [hours]

        if market in ("US", "KR"):
            query += " AND market = %s"
            params.append(market)

        cursor.execute(query, tuple(params))
        return cursor.fetchall()
