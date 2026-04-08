"""
core 패키지 - 공통 인프라 & 비즈니스 로직

사용법:
    from core.config import DB_CONFIG
    from core.db import get_db
    from core.logging_setup import setup_logging
    from core.prompts import YOUTUBE_ANALYSIS_PROMPT
    from core.ai_utils import parse_ai_json
    from core.ai_service import analyze_content, AnalysisResult
    from core.repository import save_content_analysis, get_active_sources
    from core.filters import should_save_content
    from core.notifications import send_analysis_alert
    from core.market_data import fetch_stock_price, fetch_market_indices
    from core.kiwoom_api import KiwoomConfig, KiwoomRestAPI
    from core.trading_engine import StrategyConfig, AnalysisEngine, OrderExecutor
"""
