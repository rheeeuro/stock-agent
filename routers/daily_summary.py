"""일일 요약 리포트 라우트"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.repository import (
    get_latest_daily_summary,
    get_daily_summary_by_date,
    get_daily_summary_list,
)

router = APIRouter(prefix="/api", tags=["daily-summary"])


class DailySummary(BaseModel):
    id: int
    report_date: str
    market: Optional[str] = None
    buy_stock: str
    buy_ticker: Optional[str] = None
    buy_reason: str
    sell_stock: str
    sell_ticker: Optional[str] = None
    sell_reason: str


@router.get("/daily-summary", response_model=Optional[DailySummary])
def get_daily_summary(market: str = Query("ALL", description="시장 필터 (ALL, US, KR)")):
    try:
        return get_latest_daily_summary(market=market)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-summary/{report_date}", response_model=Optional[DailySummary])
def get_daily_summary_date(report_date: str):
    """특정 날짜(YYYY-MM-DD)의 일일 요약 리포트 조회"""
    try:
        return get_daily_summary_by_date(report_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-summary-list", response_model=List[DailySummary])
def get_daily_summaries(
    limit: int = 7,
    market: str = Query("ALL", description="시장 필터 (ALL, US, KR)"),
):
    """최근 N일치의 일일 요약 리포트 목록 조회"""
    try:
        return get_daily_summary_list(limit, market=market)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
