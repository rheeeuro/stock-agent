"""텔레그램 유저 관리 라우트"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.repository import (
    VALID_ROLES,
    get_telegram_users,
    telegram_user_exists,
    create_telegram_user,
    update_telegram_user,
    delete_telegram_user,
)

router = APIRouter(prefix="/api/telegram-users", tags=["telegram-users"])


class TelegramUserCreate(BaseModel):
    id: str
    name: str
    role: str = "NORMAL"
    is_active: bool = True


class TelegramUserUpdate(BaseModel):
    name: str
    role: str = "NORMAL"
    is_active: bool = True


@router.get("")
def list_telegram_users(
    role: Optional[str] = Query(None, description="ADMIN / NORMAL"),
    is_active: Optional[bool] = Query(None),
):
    try:
        return get_telegram_users(role, is_active)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_telegram_user_route(body: TelegramUserCreate):
    chat_id = body.id.strip()
    name = body.name.strip()
    role = body.role.strip().upper()
    if not chat_id or not name:
        raise HTTPException(status_code=400, detail="id와 name은 필수입니다.")
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"role은 {sorted(VALID_ROLES)} 중 하나여야 합니다.")
    if telegram_user_exists(chat_id):
        raise HTTPException(status_code=409, detail=f"이미 등록된 chat id입니다: {chat_id}")
    try:
        create_telegram_user(chat_id, name, role, body.is_active)
        return {"success": True, "id": chat_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{chat_id}")
def update_telegram_user_route(chat_id: str, body: TelegramUserUpdate):
    name = body.name.strip()
    role = body.role.strip().upper()
    if not name:
        raise HTTPException(status_code=400, detail="name은 필수입니다.")
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"role은 {sorted(VALID_ROLES)} 중 하나여야 합니다.")
    success = update_telegram_user(chat_id, name, role, body.is_active)
    if not success:
        raise HTTPException(status_code=404, detail="해당 유저를 찾을 수 없습니다.")
    return {"success": True}


@router.delete("/{chat_id}")
def delete_telegram_user_route(chat_id: str):
    success = delete_telegram_user(chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="해당 유저를 찾을 수 없습니다.")
    return {"success": True}
