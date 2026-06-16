# Backend

FastAPI + PostgreSQL，Python 3.11，uv 管理依赖。

## 启动

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

API 文档：http://localhost:8000/docs

## 数据库迁移

```bash
cd backend
uv run alembic init -t async alembic   # 首次
uv run alembic revision --autogenerate -m "init"
uv run alembic upgrade head
```

## 目录结构

```
├── app/
│   ├── main.py          # FastAPI 入口
│   ├── core/            # 配置、数据库连接
│   ├── models/          # SQLAlchemy ORM 模型
│   ├── schemas/         # Pydantic 校验
│   └── api/v1/          # 路由
└── pyproject.toml
```
