"""티커별 섹터 해석기 (국장 전용)
- KR: 키움 ka10100.upName
- 캐시: ticker_dictionary.sector (TTL 1년)
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from core.db import get_db

logger = logging.getLogger(__name__)

_CACHE_TTL = timedelta(days=365)
_kiwoom_api = None  # lazy singleton


def _get_kiwoom_api():
    """KR 섹터 조회용 키움 API 인스턴스 (lazy init + ensure_token)"""
    global _kiwoom_api
    if _kiwoom_api is None:
        from core.kiwoom_api import KiwoomConfig, KiwoomRestAPI
        _kiwoom_api = KiwoomRestAPI(KiwoomConfig())
    _kiwoom_api.ensure_token()
    return _kiwoom_api


def _normalize_kr_code(ticker: str) -> str:
    """'005930.KS', '005930_NX' 등에서 6자리 코드 추출"""
    return ticker.split(".")[0].split("_")[0]


def _read_cache(ticker: str) -> Optional[str]:
    """ticker_dictionary에서 섹터 캐시 조회 (TTL 1년)"""
    with get_db() as (conn, cursor):
        cursor.execute(
            """
            SELECT sector, sector_updated_at
            FROM ticker_dictionary
            WHERE ticker_symbol = %s
              AND sector IS NOT NULL AND sector_updated_at IS NOT NULL
            ORDER BY FIELD(status, 'ACTIVE', 'PENDING', 'INACTIVE'), sector_updated_at DESC
            LIMIT 1
            """,
            (ticker,),
        )
        row = cursor.fetchone()
    if not row:
        return None
    if isinstance(row["sector_updated_at"], datetime):
        if datetime.now() - row["sector_updated_at"] > _CACHE_TTL:
            return None
    return row["sector"] or None


def _write_cache(ticker: str, sector: str, name: str = "") -> None:
    """ticker_dictionary 섹터 캐시 갱신. row 없으면 PENDING으로 생성."""
    with get_db() as (conn, cursor):
        cursor.execute(
            """
            UPDATE ticker_dictionary
            SET sector = %s, sector_updated_at = CURRENT_TIMESTAMP
            WHERE ticker_symbol = %s
            """,
            (sector, ticker),
        )
        if cursor.rowcount == 0 and name:
            try:
                cursor.execute(
                    """
                    INSERT IGNORE INTO ticker_dictionary
                        (company_name, ticker_symbol, status, sector, sector_updated_at)
                    VALUES (%s, %s, 'PENDING', %s, CURRENT_TIMESTAMP)
                    """,
                    (name, ticker, sector),
                )
            except Exception as e:
                logger.warning(f"섹터 캐시 INSERT 실패 [{ticker}]: {e}")
        conn.commit()


def _resolve_kr_sector(ticker: str) -> Optional[str]:
    code = _normalize_kr_code(ticker)
    try:
        api = _get_kiwoom_api()
        info = api.get_stock_detail_info(code)
        up_name = (info.get("upName") or "").strip()
        return up_name or None
    except Exception as e:
        logger.warning(f"키움 섹터 조회 실패 [{code}]: {e}")
        return None


def fetch_sector_from_api(ticker: str) -> Optional[str]:
    """캐시를 거치지 않고 키움 API에서 섹터를 직접 조회 (국장 전용).
    관리자 수동 트리거(티커 관리 페이지의 '섹터 로드' 버튼)에서 사용.
    DB에는 쓰지 않음 — 호출자가 update_ticker로 저장하는 경로에서 캐시도 함께 갱신.
    """
    ticker = (ticker or "").strip()
    if not ticker:
        return None
    return _resolve_kr_sector(ticker)


def resolve_sectors(related_tickers: list[dict]) -> list[dict]:
    """
    [{"ticker":"005930","name":"삼성전자"}, ...]
        →
    [{"ticker":"005930","sector":"반도체"}, ...]   (캐시/조회 실패 시 sector=None)

    국장 전용 — 키움 ka10100 기준으로 섹터를 해석한다.
    """
    if not related_tickers:
        return []

    out: list[dict] = []
    seen: dict[str, Optional[str]] = {}  # 호출 내 중복 방지

    for item in related_tickers:
        ticker = (item.get("ticker") or "").strip()
        name = (item.get("name") or "").strip()
        if not ticker:
            continue
        if ticker in seen:
            out.append({"ticker": ticker, "sector": seen[ticker]})
            continue

        sector = _read_cache(ticker)
        if sector is None:
            sector = _resolve_kr_sector(ticker)
            if sector:
                try:
                    _write_cache(ticker, sector, name)
                except Exception as e:
                    logger.warning(f"섹터 캐시 갱신 실패 [{ticker}]: {e}")

        seen[ticker] = sector
        out.append({"ticker": ticker, "sector": sector})

    return out
