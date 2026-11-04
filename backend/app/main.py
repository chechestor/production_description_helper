"""Точка входа FastAPI."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .db import init_db

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    path = init_db()
    logger.info("SQLite: %s", path)
    yield


app = FastAPI(title="Production Description Helper", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "llm_configured": settings.llm_configured}
