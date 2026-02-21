import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import mysql.connector
from datetime import datetime
from typing import List, Optional
from datetime import date
from dotenv import load_dotenv
from typing import List
import yfinance as yf

load_dotenv()

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

# 2. DB 설정 (.env의 DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT 사용)
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'user': os.getenv('DB_USER', 'stock_user'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'stock_agent'),
    'port': int(os.getenv('DB_PORT', '3307')),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'use_unicode': True,
}

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

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# --- API 엔드포인트 ---

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Stock Agent API"}

@app.get("/api/contents", response_model=List[ContentAnalysis])
def get_contents(limit: int = 20):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        query = """
            SELECT 
                id, external_id, source_name, title, 
                analysis_content, sentiment_score, 
                platform, source_url, created_at 
            FROM content_analysis 
            ORDER BY created_at DESC 
        LIMIT %s
        """
        cursor.execute(query, (limit,))
        result = cursor.fetchall()
                
        # created_at을 문자열로 변환 (JSON 직렬화 위해)
        for row in result:
            if row['created_at']:
                row['created_at'] = str(row['created_at'])
            # 혹시 NULL이면 50점으로 채움
            if row['sentiment_score'] is None:
                row['sentiment_score'] = 50
                
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/api/channels")
def get_channels():
    """모니터링 중인 채널 목록"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM sources WHERE platform = 'youtube'")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@app.get("/api/daily-summary", response_model=Optional[DailySummary])
def get_daily_summary():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 가장 최신 리포트 1개만 조회
        query = """
            SELECT * FROM daily_summary 
            ORDER BY report_date DESC, id DESC 
            LIMIT 1
        """
        cursor.execute(query)
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            # 날짜 객체를 문자열로 변환
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
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT * FROM daily_summary 
            WHERE report_date = %s 
            LIMIT 1
        """
        cursor.execute(query, (report_date,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
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
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 최근 날짜순으로 limit 개수만큼 가져옵니다
        query = """
            SELECT * FROM daily_summary 
            ORDER BY created_at DESC 
            LIMIT %s
        """
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
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
        # yfinance를 통해 주식 정보 가져오기
        stock = yf.Ticker(ticker)
        
        # 최근 2일치 데이터를 가져와서 전일 대비 등락률 계산
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