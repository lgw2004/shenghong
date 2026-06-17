import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session
from app.models.root_word import RootWordCheck, RootWordCheckLog, RootWordCheckTitle
from app.services.crawler import crawl_amazon
from app.services.minio_client import upload_screenshot

logger = logging.getLogger(__name__)


async def process_one(
    db: AsyncSession,
    record: RootWordCheck,
) -> RootWordCheckLog:
    """
    处理单条 root_word_check 记录（一次浏览器会话完成搜索+匹配+截图）。
    """
    # Step 1: 搜索 + 匹配 + 截图（一个浏览器会话）
    search_results, matched, screenshot_bytes = await crawl_amazon(
        website=record.website or "",
        root_word=record.root_word or "",
        site_code=record.site_code,
        keywords_str=record.keywords or "",
    )

    # 随机抖动间隔（防止被 Amazon 检测到规律性请求）
    import random
    jitter = settings.crawler_delay_seconds + random.uniform(0.5, 2.5)
    await asyncio.sleep(jitter)

    # Step 2: 保存所有搜索标题到 root_word_check_title
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

    # Step 3: 确定 root_word_type
    if matched and matched.get("url"):
        root_word_type = "0"
        matched_keyword = matched["matched_keyword"]
        keywords_log = f"matched: {matched_keyword} | original: {record.keywords}"
    else:
        root_word_type = "1"
        matched_keyword = None
        keywords_log = record.keywords or ""

    # Step 4: 上传截图到 MinIO（失败则存本地）
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
        matched_keyword or "none",
    )
    return log_record


async def process_batch(
    db: AsyncSession,
    root_word_ids: list[int] | None = None,
    limit: int = 10,
) -> list[dict]:
    """
    批量处理（并发）。

    Args:
        db: 数据库会话（仅用于查询记录列表）
        root_word_ids: 指定处理的 ID 列表，为 None 则取最新 N 条
        limit: 限制处理条数
    """
    # 查询待处理记录
    if root_word_ids:
        stmt = select(RootWordCheck).where(RootWordCheck.root_word_id.in_(root_word_ids))
    else:
        stmt = select(RootWordCheck).order_by(RootWordCheck.uptime.desc()).limit(limit)

    rows = (await db.execute(stmt)).scalars().all()

    # 并发控制信号量
    sem = asyncio.Semaphore(settings.crawler_concurrency)

    async def process_one_concurrent(record: RootWordCheck, index: int) -> dict:
        """每个并发任务使用独立的数据库会话"""
        async with sem:
            logger.info("Processing %d/%d: root_word_id=%d", index + 1, len(rows), record.root_word_id)
            async with async_session() as session:
                try:
                    log = await process_one(session, record)
                    return {
                        "root_word_id": record.root_word_id,
                        "root_word_type": log.root_word_type,
                        "check_remark": log.check_remark,
                    }
                except Exception as e:
                    logger.error("Failed root_word_id=%d: %s", record.root_word_id, e)
                    return {
                        "root_word_id": record.root_word_id,
                        "root_word_type": "-1",
                        "check_remark": str(e),
                    }

    # 并发执行
    tasks = [process_one_concurrent(r, i) for i, r in enumerate(rows)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 展平结果（处理 gather 可能返回 Exception 的情况）
    final_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            final_results.append({
                "root_word_id": rows[i].root_word_id if i < len(rows) else 0,
                "root_word_type": "-1",
                "check_remark": str(result),
            })
        else:
            final_results.append(result)

    return final_results
