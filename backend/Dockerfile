FROM python:3.11-slim

WORKDIR /app

# 0. 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 1. Python 依赖（按 uv.lock 版本锁定，跳过 dev 依赖）
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

# 2. Playwright Chromium 浏览器 + 系统依赖
RUN uv run playwright install --with-deps chromium

# 3. 应用代码
COPY app/ ./app/

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
