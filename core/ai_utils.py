"""
AI 응답 파싱 유틸리티 - 3곳에 분산되었던 파싱 로직을 통합
"""
import re
import json
import logging


def clean_ai_response(raw_content: str) -> str:
    """
    AI 원본 응답에서 JSON만 깔끔하게 추출.
    - <think> 태그 제거 (DeepSeek-R1 대응)
    - ```json 마크다운 코드블록 제거
    - 앞뒤 공백 정리
    """
    content = raw_content.strip()

    # 1. ```json / ``` 마크다운 코드블록 제거
    content = content.replace('```json', '').replace('```', '').strip()

    # 2. <think>...</think> 태그 제거 (DeepSeek-R1 특성)
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

    # 3. 혹시 </think> 태그만 남아있을 경우 뒤쪽만 남기기
    if '</think>' in content:
        content = content.split('</think>')[-1].strip()

    return content


def parse_ai_json(raw_content: str) -> dict | None:
    """
    AI 응답 문자열에서 JSON 객체를 파싱하여 반환.
    파싱 실패 시 None 반환.
    """
    cleaned = clean_ai_response(raw_content)

    # { } 블록 찾기 (정규식)
    match = re.search(r'\{.*\}', cleaned, flags=re.DOTALL)
    if not match:
        logging.error("❌ AI 응답에서 JSON 괄호 '{ }' 를 찾을 수 없습니다.")
        return None

    json_str = match.group(0)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logging.error(f"❌ JSON 디코딩 에러: {e}")
        logging.error(f"추출하려던 텍스트: {json_str}")
        return None


def remove_markdown_code_blocks(content: str) -> str:
    """분석 결과 저장 시 앞뒤의 markdown 코드 블록 마커 제거"""
    if not content:
        return content

    content = content.strip()

    # 앞에서 시작하는 ``` 제거 (언어 태그 포함)
    content = re.sub(r'^```[a-zA-Z]*\s*\n?', '', content, flags=re.MULTILINE)
    content = re.sub(r'^```\s*\n?', '', content, flags=re.MULTILINE)

    # 뒤에서 끝나는 ``` 제거
    content = re.sub(r'\r?\n```\s*$', '', content)
    content = re.sub(r'```\s*$', '', content)

    return content.strip()
