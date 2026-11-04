"""Точка входа FastAPI."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from starlette.concurrency import run_in_threadpool

from . import config
from .auth import require_session
from .auth import router as auth_router
from .db import init_db
from .errors import install_error_handlers
from .generation.graph import run_generation
from .tracing import setup_tracing, shutdown_tracing
from .validation import validate_body

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    path = init_db()
    logger.info("SQLite: %s", path)
    setup_tracing()
    yield
    shutdown_tracing()


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
    # Граф LangGraph синхронный: выполняется в пуле потоков, не блокируя сервер (F005)
    return await run_in_threadpool(run_generation, validated)
