import re
import warnings
import yfinance as yf
from ddgs import DDGS

warnings.filterwarnings("ignore")

def _get_single_ticker(company_name, market='KR'):
    market = market.upper()
    
    with DDGS() as ddgs:
        # 1. 시장별 맞춤형 검색 쿼리 생성
        if market == 'KR':
            query = f"{company_name} 코스피 코스닥 종목코드"
        else:
            query = f"{company_name} {market} stock ticker symbol"
            
        try:
            results = list(ddgs.text(query, max_results=8))
            combined_text = " ".join([f"{res.get('title')} {res.get('body')} {res.get('href')}" for res in results]).upper()
            
            # 2. 시장별 티커 추출 로직 분기
            if market == 'KR':
                # 한국: 숫자 6자리 패턴 추출
                codes = re.findall(r'\b(\d{6})\b', combined_text)
                if codes:
                    for code in list(dict.fromkeys(codes)): # 중복 제거
                        for suffix in ['.KS', '.KQ']:
                            ticker = f"{code}{suffix}"
                            # 유효성 검사 (데이터가 있는지 확인)
                            if len(yf.Ticker(ticker).history(period="1d")) > 0:
                                return ticker
                                
            elif market == 'US':
                # 미국: URL 패턴(/QUOTE/SYMBOL) 또는 괄호 안의 대문자 추출
                url_match = re.findall(r'FINANCE\.YAHOO\.COM/QUOTE/([A-Z]{1,5})', combined_text)
                if url_match:
                    return url_match[0]
                
                # 괄호 안의 1~5자 대문자 (예: (AAPL), (TSLA))
                bracket_match = re.findall(r'\(?([A-Z]{1,5})\)?', combined_text)
                blacklist = {'HTTPS', 'HTTP', 'WWW', 'STOCK', 'NYSE', 'NASDAQ', 'USD'}
                for m in bracket_match:
                    if m not in blacklist: return m

        except Exception:
            pass

    # 3. 최후의 수단: yfinance Search API (시장 필터 적용)
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

def get_tickers_by_market(names: list[str], market: str = 'KR') -> list[str]:
    """
    market: 'KR' (한국), 'US' (미국) 등 국가 코드
    names: 한글 또는 영문 기업명 리스트
    """
    tickers = []
    if not names:
        return tickers
        
    for name in names:
        ticker = _get_single_ticker(name, market)
        if ticker and ticker != "Not Found":
            # 중복 방지
            if ticker not in tickers:
                tickers.append(ticker)
                
    return tickers