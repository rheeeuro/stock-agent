import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import mysql.connector
from datetime import datetime
from typing import List, Optional
from datetime import date
from dotenv import load_dotenv

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
    buy_stock: Optional[str] = None
    buy_reason: Optional[str] = None
    sell_stock: Optional[str] = None
    sell_reason: Optional[str] = None

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