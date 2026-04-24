"""
공통 설정 모듈 - DB 설정, 환경변수, 상수를 한 곳에서 관리
"""
import os
from dotenv import load_dotenv

load_dotenv()

# DB 설정
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

# 텔레그램 설정
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# 텔레그램 API (Telethon)
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')

# AI 모델 설정 (Ollama)
OLLAMA_HOST = 'http://127.0.0.1:11434'
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'exaone3.5:7.8b')

# OpenAI 설정 (일간 리포트용)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-5.4-nano')
