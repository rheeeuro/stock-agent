"""
공통 로깅 설정 모듈
"""
import sys
import logging


def setup_logging(level=logging.INFO):
    """프로젝트 공통 로깅 포맷 설정"""
    logging.basicConfig(
        level=level,
        format='[%(asctime)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stdout
    )
