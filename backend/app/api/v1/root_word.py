import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.root_word import RootWordCheck, RootWordCheckLog
from app.services.root_word_service import process_batch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/root-word", tags=["root-word"])


class ProcessResponse(BaseModel):
    total: int
    matched: int
    unmatched: int
    results: list[dict]


class LogListResponse(BaseModel):
    total: int
    items: list[dict]


@router.post("/process", response_model=ProcessResponse)
async def trigger_process(
    root_word_ids: Optional[str] = Query(None, description="逗号分隔的 root_word_id 列表，不传则取最新"),
    limit: int = Query(10, ge=1, le=100, description="最多处理条数"),
    db: AsyncSession = Depends(get_db),
):
    """
    触发词根校验处理：

    - 搜索 → 匹配 → 截图 → 写日志
    - 指定 root_word_ids 时只处理这些，否则取最新 N 条
    """
    ids = None
    if root_word_ids:
        ids = [int(x.strip()) for x in root_word_ids.split(",") if x.strip()]

    results = await process_batch(db, root_word_ids=ids, limit=limit)

    matched = sum(1 for r in results if r["root_word_type"] == "0")
    unmatched = sum(1 for r in results if r["root_word_type"] == "1")

    return ProcessResponse(
        total=len(results),
        matched=matched,
        unmatched=unmatched,
        results=results,
    )


@router.get("/logs", response_model=LogListResponse)
async def list_logs(
    root_word_id: Optional[int] = Query(None, description="筛选词根ID"),
    root_word_type: Optional[str] = Query(None, description="0有效 1无效"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """查询校验日志"""
    conditions = []
    if root_word_id is not None:
        conditions.append(RootWordCheckLog.root_word_id == root_word_id)
    if root_word_type is not None:
        conditions.append(RootWordCheckLog.root_word_type == root_word_type)

    stmt = select(RootWordCheckLog).order_by(RootWordCheckLog.uptime.desc())
    count_stmt = select(RootWordCheckLog)

    if conditions:
        stmt = stmt.where(*conditions)
        count_stmt = count_stmt.where(*conditions)

    from sqlalchemy import func

    count_stmt = select(func.count()).select_from(RootWordCheckLog)
    if conditions:
        count_stmt = count_stmt.where(*conditions)

    total = (await db.execute(count_stmt)).scalar() or 0
    rows = (await db.execute(stmt.limit(limit).offset(offset))).scalars().all()

    items = [
        {
            "id": r.id,
            "root_word_id": r.root_word_id,
            "website": r.website,
            "root_word": r.root_word,
            "root_word_type": r.root_word_type,
            "check_remark": r.check_remark,
            "erp_api_status": r.erp_api_status,
            "uptime": r.uptime.isoformat() if r.uptime else None,
        }
        for r in rows
    ]

    return LogListResponse(total=total, items=items)


@router.get("/source")
async def list_source(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """查询来源表 root_word_check"""
    from sqlalchemy import func

    stmt = select(RootWordCheck).order_by(RootWordCheck.uptime.desc()).limit(limit).offset(offset)
    count_stmt = select(func.count()).select_from(RootWordCheck)

    total = (await db.execute(count_stmt)).scalar() or 0
    rows = (await db.execute(stmt)).scalars().all()

    items = [
        {
            "root_word_id": r.root_word_id,
            "platform_code": r.platform_code,
            "platform_name": r.platform_name,
            "site_code": r.site_code,
            "site_name": r.site_name,
            "website": r.website,
            "root_word": r.root_word,
            "keywords": r.keywords,
            "uptime": r.uptime.isoformat() if r.uptime else None,
        }
        for r in rows
    ]

    return {"total": total, "items": items}
