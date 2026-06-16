import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.root_word import RootWordCheck, RootWordCheckLog, RootWordCheckTitle
from app.services.crawler import _build_search_url, search_amazon, take_screenshot
from app.services.matcher import match_keywords
from app.services.minio_client import upload_screenshot

logger = logging.getLogger(__name__)


async def process_one(
    db: AsyncSession,
    record: RootWordCheck,
) -> RootWordCheckLog:
    """
    处理单条 root_word_check 记录：

    1. 在对应站点搜索 root_word
    2. 拆分 keywords 匹配搜索结果
    3. 命中 → 截图 → 上传 MinIO → 写日志（root_word_type='0'）
    4. 未命中 → 写日志（root_word_type='1'）
    """
    search_results = []

    # Step 1: 搜索
    if record.website:
        search_results = await search_amazon(
            website=record.website,
            root_word=record.root_word or "",
            site_code=record.site_code,
        )
        # 请求间隔
        await asyncio.sleep(settings.crawler_delay_seconds)

    # Step 2: 匹配
    matched = match_keywords(
        keywords_str=record.keywords or "",
        search_results=search_results,
    )

    # 保存所有搜索标题到 root_word_check_title（先删旧数据再写新数据）
    from sqlalchemy import delete as sa_delete
    await db.execute(
        sa_delete(RootWordCheckTitle).where(RootWordCheckTitle.root_word_id == record.root_word_id)
    )
    matched_title = matched.get("title") if matched else None
    for sr in search_results:
        keyword = matched.get("matched_keyword") if matched and sr.get("title") == matched_title else None
        db.add(
            RootWordCheckTitle(
                root_word_id=record.root_word_id,
                title=sr.get("title", ""),
                product_url=sr.get("url", ""),
                keyword_matched=keyword,
            )
        )
    await db.flush()

    # Step 3: 确定截图目标 URL 和 root_word_type
    if matched and matched.get("url"):
        root_word_type = "0"
        matched_keyword = matched["matched_keyword"]
        target_url = matched["url"]
        keywords_log = f"matched: {matched_keyword} | original: {record.keywords}"
    else:
        root_word_type = "1"
        matched_keyword = None
        target_url = _build_search_url(record.website or "", record.root_word or "")
        keywords_log = record.keywords or ""

    # Step 4: 截图 + MinIO（MinIO 失败则存本地）
    screenshot_bytes = await take_screenshot(target_url)
    if screenshot_bytes:
        filename = f"{uuid.uuid4().hex[:12]}.png"
        try:
            screenshot_url = await upload_screenshot(
                root_word_id=record.root_word_id,
                image_bytes=screenshot_bytes,
                filename=filename,
            )
            check_remark = screenshot_url
        except Exception as e:
            # MinIO 不可用时存本地
            import os
            local_dir = os.path.join(os.path.dirname(__file__), "..", "..", "screenshots")
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, f"{record.root_word_id}_{filename}")
            with open(local_path, "wb") as f:
                f.write(screenshot_bytes)
            check_remark = f"local://{local_path}"
            logger.warning("MinIO failed, saved locally: %s", local_path)
    else:
        check_remark = "screenshot failed"

    log_record = RootWordCheckLog(
        root_word_id=record.root_word_id,
        website=record.website or "",
        root_word=record.root_word or "",
        keywords=keywords_log,
        root_word_type=root_word_type,
        check_remark=check_remark,
        erp_api_status="0",
    )
    db.add(log_record)
    await db.commit()
    await db.refresh(log_record)

    logger.info(
        "root_word_id=%d, type=%s, matched=%s",
        record.root_word_id,
        root_word_type,
        matched.get("matched_keyword") if matched else "none",
    )
    return log_record


async def process_batch(
    db: AsyncSession,
    root_word_ids: list[int] | None = None,
    limit: int = 10,
) -> list[dict]:
    """
    批量处理。

    Args:
        db: 数据库会话
        root_word_ids: 指定处理的 ID 列表，为 None 则取最新 N 条
        limit: 限制处理条数
    """
    results = []

    if root_word_ids:
        stmt = select(RootWordCheck).where(RootWordCheck.root_word_id.in_(root_word_ids))
    else:
        stmt = select(RootWordCheck).order_by(RootWordCheck.uptime.desc()).limit(limit)

    rows = (await db.execute(stmt)).scalars().all()

    for i, record in enumerate(rows):
        logger.info("Processing %d/%d: root_word_id=%d", i + 1, len(rows), record.root_word_id)
        try:
            log = await process_one(db, record)
            results.append({
                "root_word_id": record.root_word_id,
                "root_word_type": log.root_word_type,
                "check_remark": log.check_remark,
            })
        except Exception as e:
            logger.error("Failed root_word_id=%d: %s", record.root_word_id, e)
            results.append({
                "root_word_id": record.root_word_id,
                "root_word_type": "-1",
                "check_remark": str(e),
            })

        # 每条处理完都间隔
        if i < len(rows) - 1:
            await asyncio.sleep(settings.crawler_delay_seconds)

    return results
