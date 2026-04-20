"""소스(채널) 데이터 접근"""
from datetime import datetime

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


def get_sources(platform: str | None = None, is_active: bool | None = None) -> list[dict]:
    """sources 전체 조회. platform, is_active 필터 가능"""
    with get_db() as (conn, cursor):
        conditions: list[str] = []
        params: list = []
        if platform:
            conditions.append("platform = %s")
            params.append(platform)
        if is_active is not None:
            conditions.append("is_active = %s")
            params.append(bool(is_active))

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        cursor.execute(
            f"SELECT * FROM sources{where} ORDER BY platform, id DESC",
            params,
        )

        results = cursor.fetchall()
        for row in results:
            if isinstance(row.get("created_at"), datetime):
                row["created_at"] = row["created_at"].isoformat()
            if "is_active" in row:
                row["is_active"] = bool(row["is_active"])
        return results


def source_exists(platform: str, identifier: str, exclude_id: int | None = None) -> bool:
    """동일 platform + identifier 조합이 이미 존재하는지 확인 (수정 시 exclude_id로 본인 제외)"""
    with get_db() as (conn, cursor):
        if exclude_id is None:
            cursor.execute(
                "SELECT 1 FROM sources WHERE platform = %s AND identifier = %s LIMIT 1",
                (platform, identifier),
            )
        else:
            cursor.execute(
                "SELECT 1 FROM sources WHERE platform = %s AND identifier = %s AND id != %s LIMIT 1",
                (platform, identifier, exclude_id),
            )
        return cursor.fetchone() is not None


def create_source(platform: str, identifier: str, name: str | None, is_active: bool) -> int:
    """sources 새 항목 추가 — 생성된 id 반환"""
    with get_db() as (conn, cursor):
        cursor.execute(
            """
            INSERT INTO sources (platform, identifier, name, is_active)
            VALUES (%s, %s, %s, %s)
            """,
            (platform, identifier, name, bool(is_active)),
        )
        conn.commit()
        return cursor.lastrowid


def update_source(source_id: int, platform: str, identifier: str, name: str | None, is_active: bool) -> bool:
    """sources 항목 수정"""
    with get_db() as (conn, cursor):
        cursor.execute(
            """
            UPDATE sources
            SET platform = %s, identifier = %s, name = %s, is_active = %s
            WHERE id = %s
            """,
            (platform, identifier, name, bool(is_active), source_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_source(source_id: int) -> bool:
    """sources 항목 삭제"""
    with get_db() as (conn, cursor):
        cursor.execute("DELETE FROM sources WHERE id = %s", (source_id,))
        conn.commit()
        return cursor.rowcount > 0
