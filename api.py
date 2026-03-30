from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import date
from typing import List, Optional
import yfinance as yf
from pykrx import stock as pykrx_stock
import re

from core.repository import (
    get_contents_paginated,
    get_youtube_sources,
    get_latest_daily_summary,
    get_daily_summary_by_date,
    get_daily_summary_list,
    get_contents_by_ticker,
    get_ticker_dictionary,
    update_ticker,
    delete_ticker,
    lookup_name_by_ticker,
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
    """티커로 종목명을 조회합니다.
    - ticker_dictionary에서 우선 조회
    - 한국 종목(예: 005930.KS, 035420.KQ)은 pykrx로 한글 종목명 조회
    - 실패하면 yfinance의 shortName/longName/displayName 사용
    - 전부 실패하면 원래 ticker 반환
    """
    original_ticker = ticker
    ticker = ticker.strip().upper()

    # 1) ticker_dictionary에서 우선 조회
    dict_name = lookup_name_by_ticker(ticker)
    if dict_name:
        return {"name": dict_name}

    # 2) 한국 종목이면 pykrx로 한글명 조회
    m = re.match(r"^(\d{6})\.(KS|KQ)$", ticker)
    if m:
        code = m.group(1)
        try:
            kr_name = pykrx_stock.get_market_ticker_name(code)
            if kr_name:
                return {"name": kr_name}
        except Exception:
            pass

    # 3) yfinance 폴백
    try:
        stock = yf.Ticker(ticker)
        info = stock.get_info()
        name = (
            info.get("displayName")
            or info.get("shortName")
            or info.get("longName")
            or original_ticker
        )
        return {"name": name}
    except Exception:
        return {"name": original_ticker}


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


# --- Ticker Dictionary ---

class TickerDictionaryUpdate(BaseModel):
    company_name: str
    ticker_symbol: str
    market: str = "KR"  # 'KR', 'US'
    status: str  # 'PENDING', 'ACTIVE', 'INACTIVE'


@app.get("/api/ticker-dictionary")
def get_ticker_dict(status: Optional[str] = Query(None, description="상태 필터 (PENDING, ACTIVE, INACTIVE)")):
    """ticker dictionary 목록 조회"""
    try:
        return get_ticker_dictionary(status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/ticker-dictionary/{ticker_id}")
def update_ticker_dict(ticker_id: int, body: TickerDictionaryUpdate):
    """ticker dictionary 항목 수정 (이름, 심볼, 상태 변경)"""
    if body.status not in ("PENDING", "ACTIVE", "INACTIVE"):
        raise HTTPException(status_code=400, detail="status는 PENDING, ACTIVE, INACTIVE 중 하나여야 합니다.")
    success = update_ticker(ticker_id, body.company_name, body.ticker_symbol, body.market, body.status)
    if not success:
        raise HTTPException(status_code=404, detail="해당 항목을 찾을 수 없습니다.")
    return {"success": True}


@app.delete("/api/ticker-dictionary/{ticker_id}")
def delete_ticker_dict(ticker_id: int):
    """ticker dictionary 항목 삭제"""
    success = delete_ticker(ticker_id)
    if not success:
        raise HTTPException(status_code=404, detail="해당 항목을 찾을 수 없습니다.")
    return {"success": True}
