"""전략 설정 라우트"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from core.repository import get_strategy_config, update_strategy_config

router = APIRouter(prefix="/api", tags=["strategy-config"])


class StrategyConfigResponse(BaseModel):
    # 필터 임계값
    MIN_TRADING_VALUE: int = 0
    PREFERRED_TRADING_VALUE: int = 0
    MIN_MARKET_CAP: int = 0
    TOP_N_BY_VALUE: int = 20
    # 이동평균
    MA_PERIODS: List[int] = [5, 10, 20]
    # 수급 기준
    MIN_INST_NET_BUY_AMT: int = 0
    MIN_FRGN_NET_BUY_AMT: int = 0
    SUPPLY_CHECK_DAYS: int = 5
    # 테마
    TOP_THEME_COUNT: int = 8
    THEME_PERIOD_DAYS: str = "10"
    THEME_STOCK_BONUS: int = 15
    # 콘텐츠 분석
    CONTENT_SCORE_MAX: int = 10
    # 제외 키워드
    EXCLUDE_KEYWORDS: List[str] = []


@router.get("/strategy-config", response_model=StrategyConfigResponse)
def get_config():
    """현재 전략 설정 조회"""
    try:
        return get_strategy_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/strategy-config", response_model=StrategyConfigResponse)
def put_config(body: StrategyConfigResponse):
    """전략 설정 업데이트"""
    try:
        return update_strategy_config(body.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
