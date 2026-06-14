"""소스 관리 라우트"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.repository import (
    get_sources,
    source_exists,
    create_source,
    update_source,
    delete_source,
)

router = APIRouter(prefix="/api/sources", tags=["sources"])


class SourceCreate(BaseModel):
    platform: str
    identifier: str
    name: Optional[str] = None
    is_active: bool = True


class SourceUpdate(BaseModel):
    platform: str
    identifier: str
    name: Optional[str] = None
    is_active: bool = True


@router.get("")
def list_sources(
    platform: Optional[str] = Query(None, description="플랫폼 필터 (youtube, telegram 등)"),
    is_active: Optional[bool] = Query(None, description="활성 여부 필터"),
):
    """sources 목록 조회"""
    try:
        return get_sources(platform, is_active)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_source_route(body: SourceCreate):
    """sources 새 항목 추가"""
    platform = body.platform.strip()
    identifier = body.identifier.strip()
    if not platform or not identifier:
        raise HTTPException(status_code=400, detail="platform과 identifier는 필수입니다.")
    if source_exists(platform, identifier):
        raise HTTPException(
            status_code=409,
            detail=f"이미 등록된 식별자입니다: {platform} / {identifier}",
        )
    try:
        source_id = create_source(
            platform,
            identifier,
            body.name.strip() if body.name else None,
            body.is_active,
        )
        return {"success": True, "id": source_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{source_id}")
def update_source_route(source_id: int, body: SourceUpdate):
    """sources 항목 수정"""
    platform = body.platform.strip()
    identifier = body.identifier.strip()
    if not platform or not identifier:
        raise HTTPException(status_code=400, detail="platform과 identifier는 필수입니다.")
    if source_exists(platform, identifier, exclude_id=source_id):
        raise HTTPException(
            status_code=409,
            detail=f"이미 등록된 식별자입니다: {platform} / {identifier}",
        )
    success = update_source(
        source_id,
        platform,
        identifier,
        body.name.strip() if body.name else None,
        body.is_active,
    )
    if not success:
        raise HTTPException(status_code=404, detail="해당 항목을 찾을 수 없습니다.")
    return {"success": True}


@router.delete("/{source_id}")
def delete_source_route(source_id: int):
    """sources 항목 삭제"""
    success = delete_source(source_id)
    if not success:
        raise HTTPException(status_code=404, detail="해당 항목을 찾을 수 없습니다.")
    return {"success": True}
