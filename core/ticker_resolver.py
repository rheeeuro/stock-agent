"""
기업명 → 티커 심볼 변환 모듈 - yfinance Search API 활용
"""
import logging

import yfinance as yf


def resolve_company_to_ticker(company_name: str) -> str | None:
    """yfinance에서 기업명으로 티커 심볼을 검색하여 반환"""
    try:
        search = yf.Search(company_name)
        if search.quotes:
            symbol = search.quotes[0]["symbol"]
            logging.info(f"🔗 티커 변환: '{company_name}' → {symbol}")
            return symbol
    except Exception as e:
        logging.warning(f"⚠️ 티커 검색 실패 ({company_name}): {e}")
    return None


def resolve_companies_to_tickers(company_names: list[str]) -> list[str]:
    """기업명 리스트를 티커 심볼 리스트로 변환 (검색 실패한 항목은 제외)"""
    tickers = []
    for name in company_names:
        ticker = resolve_company_to_ticker(name)
        if ticker:
            tickers.append(ticker)
    return tickers
