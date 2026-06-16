from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RootWordCheck(Base):
    """词根校验表（来源ERP视图）"""

    __tablename__ = "root_word_check"

    root_word_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    platform_code: Mapped[str | None] = mapped_column(String(200))
    platform_name: Mapped[str | None] = mapped_column(String(500))
    main_category_code: Mapped[str | None] = mapped_column(String(200))
    main_category_name: Mapped[str | None] = mapped_column(String(500))
    site_code: Mapped[str | None] = mapped_column(String(200))
    site_name: Mapped[str | None] = mapped_column(String(500))
    website: Mapped[str | None] = mapped_column(String(500))
    root_word: Mapped[str | None] = mapped_column(String(500))
    keywords: Mapped[str | None] = mapped_column(Text)
    uptime: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class RootWordCheckLog(Base):
    """词根校验日志表"""

    __tablename__ = "root_word_check_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    root_word_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    website: Mapped[str] = mapped_column(String(500), nullable=False)
    root_word: Mapped[str] = mapped_column(String(500), nullable=False)
    keywords: Mapped[str] = mapped_column(Text, nullable=False)
    root_word_type: Mapped[str] = mapped_column(String(10), nullable=False)
    check_remark: Mapped[str] = mapped_column(String(1024), nullable=False)
    erp_api_status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="0", server_default="0"
    )
    erp_api_msg: Mapped[str | None] = mapped_column(String(1024))
    uptime: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class RootWordCheckTitle(Base):
    """词根校验标题表（抓取的搜索标题）"""

    __tablename__ = "root_word_check_title"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    root_word_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    product_url: Mapped[str | None] = mapped_column(Text)
    keyword_matched: Mapped[str | None] = mapped_column(String(500))
    uptime: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
