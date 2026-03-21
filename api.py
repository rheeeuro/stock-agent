from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import date
from typing import List, Optional
import yfinance as yf

from core.repository import (
    get_contents_paginated,
    get_youtube_sources,
    get_latest_daily_summary,
    get_daily_summary_by_date,
    get_daily_summary_list,
    get_contents_by_ticker,
    get_stock_name_from_db,
)

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ContentAnalysis(BaseModel):
    id: int
    external_id: str
    source_name: str
    title: str
    analysis_content: str
    sentiment_score: Optional[int] = 50
    platform: str
    source_url: Optional[str] = None
    created_at: str


class DailySummary(BaseModel):
    id: int
    report_date: str
    buy_stock: str
    buy_ticker: Optional[str] = None
    buy_reason: str
    sell_stock: str
    sell_ticker: Optional[str] = None
    sell_reason: str


# --- API 엔드포인트 ---

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Stock Agent API"}


@app.get("/api/contents")
def get_contents(
    page: int = Query(1, description="현재 페이지 번호"),
    limit: int = Query(12, description="페이지 당 항목 수"),
    market: str = Query("ALL", description="시장 필터 (ALL, US, KR 등)")
):
    try:
        result = get_contents_paginated(page, limit, market)
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/channels")
def get_channels():
    """모니터링 중인 채널 목록"""
    return get_youtube_sources()


@app.get("/api/daily-summary", response_model=Optional[DailySummary])
def get_daily_summary():
    try:
        return get_latest_daily_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/daily-summary/{report_date}", response_model=Optional[DailySummary])
def get_daily_summary_date(report_date: str):
    """특정 날짜(YYYY-MM-DD)의 일일 요약 리포트 조회"""
    try:
        return get_daily_summary_by_date(report_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/daily-summary-list", response_model=List[DailySummary])
def get_daily_summaries(limit: int = 7):
    """최근 N일치의 일일 요약 리포트 목록 조회"""
    try:
        return get_daily_summary_list(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock-price/{ticker}")
def get_stock_price(ticker: str):
    """야후 파이낸스를 통해 실시간 주가 및 등락률 조회"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="2d")

        if hist.empty or len(hist) < 1:
            return {"error": "데이터를 찾을 수 없습니다."}

        current_price = hist['Close'].iloc[-1]

        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            change = current_price - prev_close
            change_percent = (change / prev_close) * 100
        else:
            change = 0.0
            change_percent = 0.0

        return {
            "ticker": ticker,
            "price": round(current_price, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/contents/{ticker}", response_model=List[ContentAnalysis])
def get_ticker_contents(ticker: str):
    """특정 티커(종목)와 관련된 콘텐츠 조회"""
    try:
        return get_contents_by_ticker(ticker)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock-name/{ticker}")
def get_stock_name(ticker: str):
    """DB 기록을 뒤져서 티커의 한글 종목명을 찾아옵니다"""
    return {"name": get_stock_name_from_db(ticker)}


@app.get("/api/stock-history/{ticker}")
def get_stock_history(ticker: str):
    """최근 7일 주가 데이터 가져오기 (차트 오버레이용)"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="7d")

        result = []
        if not hist.empty:
            for dt, row in hist.iterrows():
                result.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "price": round(row['Close'], 2)
                })
        return result
    except Exception as e:
        return []
