"""텔레그램 전송 대상 유저 데이터 접근"""
from datetime import datetime

from core.db import get_db


VALID_ROLES = {"ADMIN", "NORMAL"}


def _normalize(row: dict) -> dict:
    if isinstance(row.get("created_at"), datetime):
        row["created_at"] = row["created_at"].isoformat()
    if isinstance(row.get("updated_at"), datetime):
        row["updated_at"] = row["updated_at"].isoformat()
    if "is_active" in row:
        row["is_active"] = bool(row["is_active"])
    return row


def get_telegram_users(role: str | None = None, is_active: bool | None = None) -> list[dict]:
    """텔레그램 유저 목록 조회"""
    with get_db() as (conn, cursor):
        conditions: list[str] = []
        params: list = []
        if role:
            conditions.append("role = %s")
            params.append(role)
        if is_active is not None:
            conditions.append("is_active = %s")
            params.append(bool(is_active))

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        cursor.execute(
            f"SELECT * FROM telegram_users{where} ORDER BY role, name",
            params,
        )
        return [_normalize(r) for r in cursor.fetchall()]


def get_active_chat_ids(role: str | None = None) -> list[str]:
    """is_active=TRUE인 chat id 목록 반환 (role 지정 시 해당 role만)"""
    with get_db() as (conn, cursor):
        if role:
            cursor.execute(
                "SELECT id FROM telegram_users WHERE is_active = TRUE AND role = %s",
                (role,),
            )
        else:
            cursor.execute("SELECT id FROM telegram_users WHERE is_active = TRUE")
        return [r["id"] for r in cursor.fetchall()]


def telegram_user_exists(chat_id: str) -> bool:
    with get_db() as (conn, cursor):
        cursor.execute("SELECT 1 FROM telegram_users WHERE id = %s LIMIT 1", (chat_id,))
        return cursor.fetchone() is not None


def create_telegram_user(chat_id: str, name: str, role: str, is_active: bool) -> str:
    with get_db() as (conn, cursor):
        cursor.execute(
            """
            INSERT INTO telegram_users (id, name, role, is_active)
            VALUES (%s, %s, %s, %s)
            """,
            (chat_id, name, role, bool(is_active)),
        )
        conn.commit()
        return chat_id


def update_telegram_user(chat_id: str, name: str, role: str, is_active: bool) -> bool:
    with get_db() as (conn, cursor):
        cursor.execute(
            """
            UPDATE telegram_users
            SET name = %s, role = %s, is_active = %s
            WHERE id = %s
            """,
            (name, role, bool(is_active), chat_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_telegram_user(chat_id: str) -> bool:
    with get_db() as (conn, cursor):
        cursor.execute("DELETE FROM telegram_users WHERE id = %s", (chat_id,))
        conn.commit()
        return cursor.rowcount > 0
