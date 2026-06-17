"""
词根校验 API

通俗理解：
    前端告诉后端"我想查 Amazon 上卖的东西"，后端去 Amazon 搜索，
    截图存证，把结果（匹配上了/没匹配上）写到数据库，然后返回给前端。

三个接口：
    1. POST /api/v1/root-word/process  → 触发"搜索+匹配+截图"流程
    2. GET  /api/v1/root-word/logs     → 翻看历史执行记录
    3. GET  /api/v1/root-word/source   → 翻看"任务来源表"里有哪些词根
"""

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

# ---------------------------------------------------------------------------
# 路由：FastAPI 的"地址牌"
#    prefix="/root-word" → 下面所有接口地址都以 /api/v1/root-word 开头
#    tags=["root-word"]  → Swagger 文档里归到"root-word"分组
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/root-word", tags=["root-word"])


# ---------------------------------------------------------------------------
# ↓↓↓ 下面是 Pydantic 模型（"接口返回数据的形状"）
#     有了它，Swagger 文档会自动生成示例 JSON，前端也知道字段叫什么
# ---------------------------------------------------------------------------

class ProcessResponse(BaseModel):
    """process 接口的返回体"""
    total: int          # 总共处理了几条
    matched: int        # 其中匹配上的（root_word_type='0'）
    unmatched: int      # 其中没匹配上的（root_word_type='1'）
    results: list[dict] # 每条记录的详细信息（列表里每个元素是一条）


class LogListResponse(BaseModel):
    """logs 接口的返回体"""
    total: int          # 数据库里一共多少条日志
    items: list[dict]   # 当前页的实际数据


@router.post("/process", response_model=ProcessResponse)
async def trigger_process(
    # ---- 参数定义 ----
    root_word_ids: Optional[str] = Query(
        None,
        description="要处理哪些词根？逗号分隔的 ID，例如 1,2,3。不填则取最新 N 条",
    ),
    limit: int = Query(
        10,
        ge=1,      # ≥1（大于等于 1）
        le=100,    # ≤100（小于等于 100）
        description="最多处理几条？范围 1~100，默认 10",
    ),
    # ---- 数据库会话（框架自动注入，你不用管） ----
    db: AsyncSession = Depends(get_db),
):
    """
    词根校验入口：搜索 Amazon → 关键词匹配 → 截图 → 写日志

    通俗流程：
        1) 从 root_word_check 表取出要处理的记录
        2) 拿每条记录的 root_word 去对应 Amazon 站点搜索
        3) 把搜索到的商品标题和 keywords 做匹配
        4) 命中的 → 打开商品详情页截图，上传 MinIO
           未命中 → 截搜索页的图
        5) 写入 root_word_check_log 表（root_word_type='0'=命中 '1'=未命中）
        6) 把结果返回给前端
    """

    # 把前端传的 "1,2,3" 拆成 Python 列表 [1, 2, 3]
    ids = None
    if root_word_ids:
        ids = [int(x.strip()) for x in root_word_ids.split(",") if x.strip()]

    # 调用真正的业务逻辑（在 services/root_word_service.py 里）
    results = await process_batch(db, root_word_ids=ids, limit=limit)

    # 统计匹配 / 未匹配数量
    matched = sum(1 for r in results if r["root_word_type"] == "0")
    unmatched = sum(1 for r in results if r["root_word_type"] == "1")

    return ProcessResponse(
        total=len(results),
        matched=matched,
        unmatched=unmatched,
        results=results,
    )


# ===========================================================================
#  接口 2：GET /api/v1/root-word/logs
#  ───────────────────────────────────
#  查询"执行日志"——每次 process 写一条日志到这里，你可以翻看历史。
#
#  参数（都在 URL 问号后面，全部可选）：
#    root_word_id   — 只看某个词根的日志
#    root_word_type — "0"=匹配上的, "1"=没匹配的
#    limit          — 每页多少条，默认 50，范围 1~500
#    offset         — 跳过多少条（翻页用，offset=50 表示从第 51 条开始）
# ===========================================================================
@router.get("/logs", response_model=LogListResponse)
async def list_logs(
    # ---- 参数定义 ----
    root_word_id: Optional[int] = Query(
        None,
        description="筛选某个词根 ID 的日志。不填则查全部",
    ),
    root_word: Optional[str] = Query(
        None,
        description="按词根模糊搜索（LIKE %xxx%）",
    ),
    website: Optional[str] = Query(
        None,
        description="按站点网址模糊搜索",
    ),
    site_name: Optional[str] = Query(
        None,
        description="按站点中文名模糊搜索（如 美国）",
    ),
    sort: Optional[str] = Query(
        "desc",
        description="时间排序：desc=倒序（最新在前）, asc=正序（最早在前）",
    ),
    root_word_type: Optional[str] = Query(
        None,
        description="筛选类型：'0'=匹配上的, '1'=没匹配的。不填则查全部",
    ),
    limit: int = Query(
        50,
        ge=1,
        le=500,
        description="每页最多多少条？默认 50，最大 500",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="跳过前面多少条（翻页用）。0 表示第一页",
    ),
    # ---- 数据库会话（框架自动注入） ----
    db: AsyncSession = Depends(get_db),
):
    """
    翻看"词根校验历史日志"

    数据库表：root_word_check_log
    每条日志记录了一次 process 的结果：谁、哪个站点、匹配了没、截图 URL
    """

    # JOIN root_word_check 拿 site_name
    from sqlalchemy import func
    from sqlalchemy.orm import joinedload

    # 拼 WHERE 条件（前端传了啥就筛啥）
    conditions = []
    if root_word_id is not None:
        conditions.append(RootWordCheckLog.root_word_id == root_word_id)
    if root_word:
        conditions.append(RootWordCheckLog.root_word.ilike(f"%{root_word}%"))
    if website:
        conditions.append(RootWordCheckLog.website.ilike(f"%{website}%"))
    if root_word_type is not None:
        conditions.append(RootWordCheckLog.root_word_type == root_word_type)

    # site_name 在 root_word_check 表，需要 JOIN 后筛选
    if site_name:
        conditions.append(RootWordCheck.site_name.ilike(f"%{site_name}%"))

    # ---- 查总数 ----
    count_stmt = (
        select(func.count())
        .select_from(RootWordCheckLog)
        .join(RootWordCheck, RootWordCheckLog.root_word_id == RootWordCheck.root_word_id, isouter=True)
    )
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = (await db.execute(count_stmt)).scalar() or 0

    # ---- 查当前页的数据 ----
    order_clause = (
        RootWordCheckLog.uptime.asc() if sort == "asc"
        else RootWordCheckLog.uptime.desc()
    )
    stmt = (
        select(RootWordCheckLog, RootWordCheck.site_name)
        .select_from(RootWordCheckLog)
        .join(RootWordCheck, RootWordCheckLog.root_word_id == RootWordCheck.root_word_id, isouter=True)
        .order_by(order_clause)
    )
    if conditions:
        stmt = stmt.where(*conditions)
    rows = (await db.execute(stmt.limit(limit).offset(offset))).fetchall()

    # 把 ORM 对象转成字典
    items = [
        {
            "id": r.RootWordCheckLog.id,
            "root_word_id": r.RootWordCheckLog.root_word_id,
            "website": r.RootWordCheckLog.website,
            "site_name": r.site_name or "",
            "root_word": r.RootWordCheckLog.root_word,
            "root_word_type": r.RootWordCheckLog.root_word_type,
            "check_remark": r.RootWordCheckLog.check_remark,
            "erp_api_status": r.RootWordCheckLog.erp_api_status,
            "uptime": r.RootWordCheckLog.uptime.isoformat() if r.RootWordCheckLog.uptime else None,
        }
        for r in rows
    ]

    return LogListResponse(total=total, items=items)


# ===========================================================================
#  接口 3：GET /api/v1/root-word/source
#  ─────────────────────────────────────
#  查询"任务来源表"——哪些词根需要被检查（数据来源，process 接口从这里面取数）
#
#  参数：
#    limit  — 每页多少条，默认 50
#    offset — 跳过多少条（翻页用）
#
#  示例：
#    GET /api/v1/root-word/source?limit=30&offset=0
#    含义：看前 30 条待检查的词根
# ===========================================================================
@router.get("/source")
async def list_source(
    limit: int = Query(
        50,
        ge=1,
        le=500,
        description="每页最多多少条？默认 50，最大 500",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="跳过前面多少条（翻页用）。0 表示第一页",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    翻看"任务来源表 root_word_check"

    通俗理解：
        这个表存的是"要查什么"（哪个站点、哪个词根、关键词是什么）。
        process 接口就是从这张表取数据去 Amazon 搜索的。
    """

    # ---- 查总数 ----
    from sqlalchemy import func
    count_stmt = select(func.count()).select_from(RootWordCheck)
    total = (await db.execute(count_stmt)).scalar() or 0

    # ---- 查当前页 ----
    stmt = (
        select(RootWordCheck)
        .order_by(RootWordCheck.uptime.desc())   # 按更新时间倒序（最新的在最前面）
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(stmt)).scalars().all()

    items = [
        {
            "root_word_id": r.root_word_id,
            "platform_code": r.platform_code,    # 平台代码（如 Amazon）
            "platform_name": r.platform_name,    # 平台名称
            "site_code": r.site_code,            # 站点代码（US=美国, JP=日本 等）
            "site_name": r.site_name,            # 站点名称
            "website": r.website,                # 站点网址
            "root_word": r.root_word,            # 搜索的关键词（词根）
            "keywords": r.keywords,              # 要匹配的关键词列表
            "uptime": r.uptime.isoformat() if r.uptime else None,
        }
        for r in rows
    ]

    return {"total": total, "items": items}


# ===========================================================================
#  接口 4：GET /api/v1/root-word/stats
#  ─────────────────────────────────────
#  返回 Dashboard 面板需要的汇总统计
# ===========================================================================
@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """
    BI 面板统计接口：总词根数、总日志数、命中率、按站点分布、最近日志
    """
    from sqlalchemy import func, case

    # --- 总词根数 ---
    total_sources = (await db.execute(
        select(func.count()).select_from(RootWordCheck)
    )).scalar() or 0

    # --- 总日志数 + 命中率 ---
    total_logs = (await db.execute(
        select(func.count()).select_from(RootWordCheckLog)
    )).scalar() or 0

    matched_count = (await db.execute(
        select(func.count()).select_from(RootWordCheckLog).where(RootWordCheckLog.root_word_type == "0")
    )).scalar() or 0

    matched_rate = round(matched_count / total_logs, 3) if total_logs > 0 else 0

    # --- 截图成功率 ---
    screenshot_ok = (await db.execute(
        select(func.count()).select_from(RootWordCheckLog).where(
            RootWordCheckLog.check_remark.like("http://%")
        )
    )).scalar() or 0

    # --- 按站点统计 ---
    site_stmt = (
        select(
            RootWordCheckLog.website,
            func.count().label("total"),
            func.sum(case((RootWordCheckLog.root_word_type == "0", 1), else_=0)).label("matched"),
            func.sum(case((RootWordCheckLog.root_word_type == "1", 1), else_=0)).label("unmatched"),
        )
        .group_by(RootWordCheckLog.website)
        .order_by(func.count().desc())
    )
    site_rows = (await db.execute(site_stmt)).fetchall()
    by_site = [
        {
            "website": r.website,
            "total": r.total,
            "matched": r.matched or 0,
            "unmatched": r.unmatched or 0,
        }
        for r in site_rows
    ]

    # --- 最近 10 条日志 ---
    log_stmt = (
        select(RootWordCheckLog)
        .order_by(RootWordCheckLog.uptime.desc())
        .limit(10)
    )
    log_rows = (await db.execute(log_stmt)).scalars().all()
    recent_logs = [
        {
            "id": r.id,
            "root_word_id": r.root_word_id,
            "website": r.website,
            "root_word": r.root_word,
            "root_word_type": r.root_word_type,
            "check_remark": r.check_remark,
            "uptime": r.uptime.isoformat() if r.uptime else None,
        }
        for r in log_rows
    ]

    return {
        "total_sources": total_sources,
        "total_logs": total_logs,
        "matched_count": matched_count,
        "matched_rate": matched_rate,
        "screenshot_ok": screenshot_ok,
        "by_site": by_site,
        "recent_logs": recent_logs,
    }
