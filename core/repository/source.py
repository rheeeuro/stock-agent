"""소스(채널) 데이터 접근"""
from core.db import get_db


def get_active_sources(platform: str) -> list[dict]:
    """활성화된 소스 목록 조회 (telegram / youtube)"""
    with get_db() as (conn, cursor):
        cursor.execute(
            "SELECT identifier, name FROM sources WHERE platform = %s AND is_active = TRUE",
            (platform,),
        )
        return cursor.fetchall()


def get_youtube_sources() -> list[dict]:
    """YouTube 소스 전체 조회"""
    with get_db() as (conn, cursor):
        cursor.execute("SELECT * FROM sources WHERE platform = 'youtube'")
        return cursor.fetchall()
