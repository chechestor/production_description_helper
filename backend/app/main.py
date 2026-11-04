"""Точка входа FastAPI."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request

from . import config
from .auth import require_session
from .auth import router as auth_router
from .db import init_db
from .errors import ApiError, install_error_handlers
from .validation import validate_body

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
async def generate(request: Request, _login: str = Depends(require_session)) -> dict:
    # Сначала вход (F003, зависимость), потом JSON (F004): тело читается вручную,
    # чтобы битый JSON без входа давал 401, а не 400.
    validated = validate_body(await request.body())
    # Генерация — F005
    raise ApiError(
        501,
        "not_implemented",
        "Генерация ещё не реализована",
        {"missing_fields": validated.missing_fields, "warnings": validated.warnings},
    )
