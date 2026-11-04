"""Точка входа FastAPI."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from . import config
from .auth import require_session
from .auth import router as auth_router
from .db import init_db
from .errors import ApiError, install_error_handlers

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    path = init_db()
    logger.info("SQLite: %s", path)
    yield


app = FastAPI(title="Production Description Helper", lifespan=lifespan)
install_error_handlers(app)
app.include_router(auth_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "llm_configured": config.settings.llm_configured}


@app.post("/api/generate")
def generate(_login: str = Depends(require_session)) -> dict:
    # Проверка входа (F003) уже пройдена; приём JSON и генерация — F004/F005
    raise ApiError(501, "not_implemented", "Генерация ещё не реализована")
