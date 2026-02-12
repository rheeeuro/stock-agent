import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import mysql.connector
from datetime import datetime
from typing import List, Optional
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
class VideoResponse(BaseModel):
    id: int
    video_id: str
    channel_name: str
    video_title: str
    analysis_content: str
    created_at: datetime

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# --- API 엔드포인트 ---

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Stock Agent API"}

@app.get("/api/videos", response_model=List[VideoResponse])
def get_videos(limit: int = 20):
    """최신 분석 영상 목록 조회"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        query = """
            SELECT id, video_id, channel_name, video_title, analysis_content, created_at 
            FROM video_analysis 
            ORDER BY created_at DESC 
            LIMIT %s
        """
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        return results
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
        cursor.execute("SELECT * FROM channels")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()