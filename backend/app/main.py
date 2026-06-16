from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.api.v1.root_word import router as root_word_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

# API v1
app.include_router(v1_router, prefix="/api/v1")
app.include_router(root_word_router, prefix="/api/v1")
