import re
import logging
import warnings
import yfinance as yf
from ddgs import DDGS

from core.repository import lookup_ticker, save_ticker

warnings.filterwarnings("ignore")

def _search_ticker_online(company_name, market='KR'):
    """기존 DuckDuckGo + yfinance 검색 로직 (dictionary에 없을 때 폴백)"""
    market = market.upper()
    
    with DDGS() as ddgs:
        if market == 'KR':
            query = f"{company_name} 코스피 코스닥 종목코드"
        else:
            query = f"{company_name} {market} stock ticker symbol"
            
        try:
            results = list(ddgs.text(query, max_results=8))
            combined_text = " ".join([f"{res.get('title')} {res.get('body')} {res.get('href')}" for res in results]).upper()
            
            if market == 'KR':
                codes = re.findall(r'\b(\d{6})\b', combined_text)
                if codes:
                    for code in list(dict.fromkeys(codes)):
                        for suffix in ['.KS', '.KQ']:
                            ticker = f"{code}{suffix}"
                            if len(yf.Ticker(ticker).history(period="1d")) > 0:
                                return ticker
                                
            elif market == 'US':
                url_match = re.findall(r'FINANCE\.YAHOO\.COM/QUOTE/([A-Z]{1,5})', combined_text)
                if url_match:
                    return url_match[0]
                
                bracket_match = re.findall(r'\(?([A-Z]{1,5})\)?', combined_text)
                blacklist = {'HTTPS', 'HTTP', 'WWW', 'STOCK', 'NYSE', 'NASDAQ', 'USD'}
                for m in bracket_match:
                    if m not in blacklist: return m

        except Exception:
            pass

    try:
        search = yf.Search(company_name, max_results=10).quotes
        for q in search:
            symbol = q['symbol']
            if market == 'KR' and (symbol.endswith('.KS') or symbol.endswith('.KQ')):
                return symbol
            if market == 'US' and '.' not in symbol and len(symbol) <= 5:
                return symbol
    except:
        pass

    return "Not Found"


def _get_single_ticker(company_name, market='KR'):
    """dictionary 조회 → 없으면 온라인 검색 → 결과를 dictionary에 PENDING으로 저장"""
    cached = lookup_ticker(company_name)
    if cached and cached["status"] != "INACTIVE":
        logging.info(f"📖 Dictionary 캐시 히트: {company_name} → {cached['ticker_symbol']}")
        return cached["ticker_symbol"]

    ticker = _search_ticker_online(company_name, market)

    if ticker and ticker != "Not Found":
        save_ticker(company_name, ticker, market=market, status="PENDING")
        logging.info(f"📝 Dictionary에 새 티커 저장 (임시): {company_name} → {ticker} [{market}]")

    return ticker


def get_tickers_by_market(names: list[str], market: str = 'KR') -> list[dict]:
    """
    market: 'KR' (한국), 'US' (미국) 등 국가 코드
    names: 한글 또는 영문 기업명 리스트
    반환: [{"ticker": "AAPL", "name": "Apple"}, ...] 형식
    """
    tickers = []
    if not names:
        return tickers

    seen = set()
    for name in names:
        ticker = _get_single_ticker(name, market)
        if ticker and ticker != "Not Found" and ticker not in seen:
            seen.add(ticker)
            tickers.append({"ticker": ticker, "name": name})

    return tickers