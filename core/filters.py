"""
콘텐츠 저장 여부 판단 필터 모듈
"""
import logging


def should_save_content(score: int | None, related_companies: list | None, *, skip_neutral: bool = False) -> bool:
    """
    분석 결과를 DB에 저장할지 판단.
    - 관련 기업이 없으면 저장하지 않음
    - skip_neutral=True일 때 점수가 40~70(중립) 구간이면 저장하지 않음
    """
    if not related_companies:
        logging.info("⏭️ [스킵] 구체적인 연관 기업이 없어 저장하지 않습니다.")
        return False

    if skip_neutral and score is not None and 40 <= score <= 70:
        logging.info(f"⏭️ [스킵] 점수가 {score}점(40~70 구간)이라 저장하지 않습니다.")
        return False

    return True
