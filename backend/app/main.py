"""Точка входа FastAPI."""

from fastapi import FastAPI

from .config import settings

app = FastAPI(title="Production Description Helper")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "llm_configured": settings.llm_configured}
