"""
콘텐츠 저장 여부 판단 필터 모듈
"""
import logging
import re

_URL_PATTERN = re.compile(r'https?://\S+')


def should_save_content(score: int | None, related_tickers: list[dict] | None, *, skip_neutral: bool = False, allow_no_ticker: bool = False) -> bool:
    """
    분석 결과를 DB에 저장할지 판단.
    related_tickers: [{"ticker": "AAPL", "name": "Apple"}, ...] 형식
    """
    if not related_tickers and not allow_no_ticker:
        logging.info("⏭️ [스킵] 구체적인 티커(Ticker)가 없어 저장하지 않습니다.")
        return False

    if skip_neutral and score is not None and 40 <= score <= 70:
        logging.info(f"⏭️ [스킵] 점수가 {score}점(40~70 구간)이라 저장하지 않습니다.")
        return False

    return True


def validate_analysis(original_text: str, related_companies: list[str], title: str) -> bool:
    """
    AI 분석 결과가 원문 텍스트와 일치하는지 검증 (환각 방지).
    related_companies 중 하나라도 원문에 존재하는지, title 핵심 명사가 원문에 있는지 확인.
    """
    text_clean = _URL_PATTERN.sub('', original_text).strip()

    if not text_clean or len(text_clean) < 10:
        logging.warning("🚨 [환각 방지] 원문에 실질적인 텍스트가 없어 분석 결과를 폐기합니다.")
        return False

    if related_companies:
        found = False
        for company in related_companies:
            # "삼성전자" → "삼성", "엔비디아" → "엔비디아" 등 핵심 2글자 이상으로 부분 매칭
            search_term = company[:2] if len(company) > 2 else company
            if search_term in text_clean:
                found = True
                break
        if not found:
            logging.warning(
                f"🚨 [환각 감지] AI가 추출한 기업 {related_companies}이(가) "
                f"원문에 존재하지 않습니다. 분석 결과를 폐기합니다."
            )
            return False

    if title:
        # title에서 명사급 키워드(2글자 이상 한글/영문 단어) 추출 후 원문 존재 여부 확인
        title_keywords = re.findall(r'[가-힣a-zA-Z]{2,}', title)
        stopwords = {
            '전망', '분석', '상승', '하락', '급등', '급락', '호재', '악재',
            '기대감', '우려', '영향', '관련', '시장', '부문', '발표', '실적',
            '주요', '기업', '종목', '투자', '매수', '매도', '긍정적', '부정적',
        }
        meaningful_keywords = [kw for kw in title_keywords if kw not in stopwords]

        if meaningful_keywords:
            title_match = any(kw in text_clean for kw in meaningful_keywords)
            if not title_match:
                logging.warning(
                    f"🚨 [환각 감지] AI 제목 '{title}'의 핵심 키워드 {meaningful_keywords}가 "
                    f"원문에 존재하지 않습니다. 분석 결과를 폐기합니다."
                )
                return False

    return True
