import math
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional
import yfinance as yf

from core.config import DB_CONFIG
from core.db import get_db

app = FastAPI()

# 1. CORS 설정 (Next.js 연동 필수)
origins = [
    "http://localhost:3000", # Next.js 개발 서버
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 데이터 모델 정의 (TypeScript Interface와 같은 역할)
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
        with get_db() as (conn, cursor):
            # 1. 프론트엔드에 전달할 OFFSET (건너뛸 개수) 계산
            offset = (page - 1) * limit

            where_clause = "WHERE created_at >= NOW() - INTERVAL 7 DAY"
            query_params = []
            
            if market in ["US", "KR"]:
                where_clause += " AND market = %s"
                query_params.append(market)

            # 2. 전체 데이터 개수 조회 (프론트엔드 페이지네이션 UI를 위함)
            count_query = f"SELECT COUNT(*) as total_count FROM content_analysis {where_clause}"
            cursor.execute(count_query, tuple(query_params))
            total_count = cursor.fetchone()['total_count']

            # 3. 데이터를 페이지에 맞게 잘라서(LIMIT, OFFSET) 가져오기
            data_query = f"""
                SELECT
                    id, external_id, source_name, title, 
                    analysis_content, sentiment_score, 
                    platform, market, source_url, created_at 
                FROM content_analysis 
                {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(data_query, tuple(query_params + [limit, offset]))
            result = cursor.fetchall()

            # created_at을 문자열로 변환 (JSON 직렬화 위해)
            for row in result:
                if row['created_at']:
                    row['created_at'] = str(row['created_at'])
                if row['sentiment_score'] is None:
                    row['sentiment_score'] = 50

            # 4. 전체 페이지 수 등을 함께 계산해서 JSON으로 반환
            total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

            return {
                "success": True,
                "data": result,
                "pagination": {
                    "current_page": page,
                    "limit": limit,
                    "total_items": total_count,
                    "total_pages": total_pages,
                    "has_next_page": page < total_pages,
                    "has_prev_page": page > 1
                }
            }

    except Exception as e:
        print(f"❌ DB 조회 에러: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/channels")
def get_channels():
    """모니터링 중인 채널 목록"""
    with get_db() as (conn, cursor):
        cursor.execute("SELECT * FROM sources WHERE platform = 'youtube'")
        return cursor.fetchall()

@app.get("/api/daily-summary", response_model=Optional[DailySummary])
def get_daily_summary():
    try:
        with get_db() as (conn, cursor):
            query = """
                SELECT * FROM daily_summary 
                ORDER BY report_date DESC, id DESC 
                LIMIT 1
            """
            cursor.execute(query)
            result = cursor.fetchone()
            
            if result:
                if isinstance(result['report_date'], date):
                    result['report_date'] = result['report_date'].isoformat()
                return result
            return None
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/daily-summary/{report_date}", response_model=Optional[DailySummary])
def get_daily_summary_by_date(report_date: str):
    """특정 날짜(YYYY-MM-DD)의 일일 요약 리포트 조회"""
    try:
        with get_db() as (conn, cursor):
            query = """
                SELECT * FROM daily_summary 
                WHERE report_date = %s 
                LIMIT 1
            """
            cursor.execute(query, (report_date,))
            result = cursor.fetchone()
            
            if result:
                if isinstance(result['report_date'], date):
                    result['report_date'] = result['report_date'].isoformat()
                return result
            return None
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/daily-summary-list", response_model=List[DailySummary])
def get_daily_summary_list(limit: int = 7):
    """최근 N일치의 일일 요약 리포트 목록 조회"""
    try:
        with get_db() as (conn, cursor):
            query = """
                SELECT * FROM daily_summary 
                ORDER BY created_at DESC 
                LIMIT %s
            """
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            
            # 날짜 포맷팅 (YYYY-MM-DD)
            for row in results:
                if isinstance(row['report_date'], date) or hasattr(row['report_date'], 'isoformat'):
                    row['report_date'] = str(row['report_date']).split(' ')[0]
                    
            return results
        
    except Exception as e:
        print(f"Error: {e}")
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
        print(f"yfinance 조회 에러 ({ticker}): {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contents/{ticker}", response_model=List[ContentAnalysis])
def get_contents_by_ticker(ticker: str):
    """특정 티커(종목)와 관련된 콘텐츠 조회"""
    try:
        with get_db() as (conn, cursor):
            query = """
                SELECT * FROM content_analysis 
                WHERE created_at >= NOW() - INTERVAL 7 DAY
                    AND related_tickers LIKE %s 
                ORDER BY created_at DESC
            """
            search_term = f"%{ticker}%"
            cursor.execute(query, (search_term,))
            results = cursor.fetchall()
            
            for row in results:
                if isinstance(row['created_at'], datetime):
                    row['created_at'] = row['created_at'].isoformat()
                    
            return results
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stock-name/{ticker}")
def get_stock_name(ticker: str):
    """DB 기록을 뒤져서 티커의 한글 종목명을 찾아옵니다"""
    try:
        with get_db() as (conn, cursor):
            query = """
                SELECT buy_stock AS stock_name FROM daily_summary WHERE buy_ticker = %s
                UNION
                SELECT sell_stock AS stock_name FROM daily_summary WHERE sell_ticker = %s
                LIMIT 1
            """
            cursor.execute(query, (ticker, ticker))
            result = cursor.fetchone()
            
            if result and result['stock_name']:
                return {"name": result['stock_name']}
            return {"name": ticker}
        
    except Exception as e:
        print(f"이름 찾기 에러: {e}")
        return {"name": ticker}

@app.get("/api/stock-history/{ticker}")
def get_stock_history(ticker: str):
    """최근 7일 주가 데이터 가져오기 (차트 오버레이용)"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="7d")
        
        result = []
        if not hist.empty:
            for date, row in hist.iterrows():
                result.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "price": round(row['Close'], 2)
                })
        return result
    except Exception as e:
        print(f"히스토리 조회 에러 ({ticker}): {e}")
        return []