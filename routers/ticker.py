"""티커 사전 관리 라우트"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.repository import get_ticker_dictionary, update_ticker, delete_ticker

router = APIRouter(prefix="/api/ticker-dictionary", tags=["ticker-dictionary"])


class TickerDictionaryUpdate(BaseModel):
    company_name: str
    ticker_symbol: str
    market: str = "KR"
    status: str


@router.get("")
def get_ticker_dict(
    status: Optional[str] = Query(None, description="상태 필터 (PENDING, ACTIVE, INACTIVE)"),
    market: Optional[str] = Query(None, description="시장 필터 (KR, US)"),
):
    """ticker dictionary 목록 조회"""
    try:
        return get_ticker_dictionary(status, market)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{ticker_id}")
def update_ticker_dict(ticker_id: int, body: TickerDictionaryUpdate):
    """ticker dictionary 항목 수정"""
    if body.status not in ("PENDING", "ACTIVE", "INACTIVE"):
        raise HTTPException(status_code=400, detail="status는 PENDING, ACTIVE, INACTIVE 중 하나여야 합니다.")
    success = update_ticker(ticker_id, body.company_name, body.ticker_symbol, body.market, body.status)
    if not success:
        raise HTTPException(status_code=404, detail="해당 항목을 찾을 수 없습니다.")
    return {"success": True}


@router.delete("/{ticker_id}")
def delete_ticker_dict(ticker_id: int):
    """ticker dictionary 항목 삭제"""
    success = delete_ticker(ticker_id)
    if not success:
        raise HTTPException(status_code=404, detail="해당 항목을 찾을 수 없습니다.")
    return {"success": True}
