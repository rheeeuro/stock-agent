"""
AI 분석 서비스 모듈 - AI 클라이언트와 콘텐츠 분석 파이프라인 통합
"""
import logging
from dataclasses import dataclass, field
from ollama import Client

from core.config import OLLAMA_HOST, OLLAMA_MODEL
from core.ai_utils import parse_ai_json


@dataclass
class AnalysisResult:
    """AI 분석 결과 통합 데이터 클래스"""
    title: str = ""
    content: str = ""
    sentiment_score: int = 50
    related_companies: list = field(default_factory=list)
    market: str = "UNKNOWN"


_client = Client(host=OLLAMA_HOST)


def get_ai_client() -> Client:
    """공유 AI 클라이언트 인스턴스 반환"""
    return _client


def analyze_content(prompt: str, model: str | None = None, **chat_options) -> AnalysisResult | None:
    """
    프롬프트를 AI에 전달하고 파싱된 분석 결과를 반환.
    sentiment_score가 -1이거나 파싱 실패 시 None 반환.
    """
    model = model or OLLAMA_MODEL
    try:
        kwargs = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        if chat_options:
            kwargs["options"] = chat_options

        response = _client.chat(**kwargs)
        raw_content = response["message"]["content"]
        data = parse_ai_json(raw_content)

        if data is None:
            logging.warning(f"⏭️ [스킵] AI 응답 JSON 파싱 실패. 원본 응답: {raw_content[:200]}")
            return None

        if data.get("sentiment_score") == -1:
            logging.info("⏭️ [스킵] AI가 주식 무관 콘텐츠로 판단 (sentiment_score: -1)")
            return None

        result = AnalysisResult(
            title=data.get("title", ""),
            content=data["content"],
            sentiment_score=data["sentiment_score"],
            related_companies=data.get("related_companies", []),
            market=data.get("market", "UNKNOWN"),
        )
        logging.info(
            f"🔍 AI 분석 결과: score={result.sentiment_score}, "
            f"companies={result.related_companies}, market={result.market}"
        )
        return result

    except KeyError as e:
        logging.error(f"AI 분석 에러: 응답에 필수 키 누락 - {e}")
        return None
    except Exception as e:
        logging.error(f"AI 분석 에러: {e}")
        return None
