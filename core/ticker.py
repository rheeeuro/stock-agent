import re
import logging
import warnings
import yfinance as yf
from ddgs import DDGS

from core.repository import lookup_ticker, save_ticker

warnings.filterwarnings("ignore")

def _search_ticker_online(company_name):
    """기존 DuckDuckGo + yfinance 검색 로직 (dictionary에 없을 때 폴백, 국장 전용)"""
    with DDGS() as ddgs:
        query = f"{company_name} 코스피 코스닥 종목코드"

        try:
            results = list(ddgs.text(query, max_results=8))
            combined_text = " ".join([f"{res.get('title')} {res.get('body')} {res.get('href')}" for res in results]).upper()

            codes = re.findall(r'\b(\d{6})\b', combined_text)
            if codes:
                for code in list(dict.fromkeys(codes)):
                    for suffix in ['.KS', '.KQ']:
                        ticker = f"{code}{suffix}"
                        if len(yf.Ticker(ticker).history(period="1d")) > 0:
                            return ticker

        except Exception:
            pass

    try:
        search = yf.Search(company_name, max_results=10).quotes
        for q in search:
            symbol = q['symbol']
            if symbol.endswith('.KS') or symbol.endswith('.KQ'):
                return symbol
    except:
        pass

    return "Not Found"


def _get_single_ticker(company_name):
    """dictionary 조회 → INACTIVE면 스킵 → 없으면 온라인 검색 → 결과를 dictionary에 PENDING으로 저장"""
    cached = lookup_ticker(company_name)
    if cached:
        if cached["status"] == "INACTIVE":
            logging.info(f"🚫 INACTIVE 티커 스킵: {company_name} → {cached['ticker_symbol']}")
            return None
        logging.info(f"📖 Dictionary 캐시 히트: {company_name} → {cached['ticker_symbol']}")
        return cached["ticker_symbol"]

    ticker = _search_ticker_online(company_name)

    if ticker and ticker != "Not Found":
        save_ticker(company_name, ticker, status="PENDING")
        logging.info(f"📝 Dictionary에 새 티커 저장 (임시): {company_name} → {ticker}")

    return ticker


def get_tickers(names: list[str]) -> list[dict]:
    """
    names: 한글 또는 영문 기업명 리스트
    반환: [{"ticker": "005930.KS", "name": "삼성전자"}, ...] 형식 (국장 전용)
    """
    tickers = []
    if not names:
        return tickers

    seen = set()
    for name in names:
        ticker = _get_single_ticker(name)
        if ticker and ticker != "Not Found" and ticker not in seen:
            seen.add(ticker)
            tickers.append({"ticker": ticker, "name": name})

    return tickers
