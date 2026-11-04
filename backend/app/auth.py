"""Вход по логину и паролю из .env (AUTH_LOGIN / AUTH_PASSWORD), сессии в SQLite.

Пароль нигде не хранится и не логируется: только сравнение за постоянное время.
"""

import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, Response
from pydantic import BaseModel

from . import config
from .db import connect
from .errors import ApiError

logger = logging.getLogger("uvicorn.error")

COOKIE_NAME = "session"
INVALID_CREDENTIALS = "Неверный логин или пароль"

router = APIRouter(prefix="/api")


class LoginRequest(BaseModel):
    login: str
    password: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _credentials_match(login: str, password: str) -> bool:
    s = config.settings
    # Обе проверки выполняются всегда, чтобы время ответа не выдавало, что именно неверно
    login_ok = hmac.compare_digest(login.encode("utf-8"), s.auth_login.encode("utf-8"))
    password_ok = hmac.compare_digest(password.encode("utf-8"), s.auth_password.encode("utf-8"))
    return login_ok and password_ok


def create_session(login: str) -> tuple[str, int]:
    token = secrets.token_urlsafe(32)
    created = _now()
    ttl_seconds = config.settings.session_ttl_hours * 3600
    expires = created + timedelta(seconds=ttl_seconds)
    with connect() as conn:
        conn.execute(
            "INSERT INTO sessions (id, login, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, login, created.isoformat(), expires.isoformat()),
        )
    return token, ttl_seconds


def session_login(token: str | None) -> str | None:
    """Логин действующей сессии или None (нет, просрочена, выдана под другим логином)."""
    if not token:
        return None
    with connect() as conn:
        row = conn.execute("SELECT login, expires_at FROM sessions WHERE id = ?", (token,)).fetchone()
    if row is None:
        return None
    if datetime.fromisoformat(row["expires_at"]) <= _now():
        return None
    current_login = config.settings.auth_login
    if not current_login or not hmac.compare_digest(row["login"].encode("utf-8"), current_login.encode("utf-8")):
        return None
    return row["login"]


def require_session(session: str | None = Cookie(default=None)) -> str:
    """Зависимость для защищённых маршрутов: логин или 401 unauthorized."""
    login = session_login(session)
    if login is None:
        raise ApiError(401, "unauthorized", "Требуется вход")
    return login


@router.post("/login")
def login(body: LoginRequest, response: Response) -> dict:
    s = config.settings
    if not s.auth_login or not s.auth_password:
        logger.warning("Вход невозможен: AUTH_LOGIN или AUTH_PASSWORD не заданы в .env")
        raise ApiError(503, "auth_not_configured", "Вход не настроен: задайте AUTH_LOGIN и AUTH_PASSWORD в .env")
    if not _credentials_match(body.login, body.password):
        raise ApiError(401, "invalid_credentials", INVALID_CREDENTIALS)
    token, max_age = create_session(s.auth_login)
    response.set_cookie(COOKIE_NAME, token, max_age=max_age, httponly=True, samesite="lax", path="/")
    return {"login": s.auth_login}


@router.post("/logout")
def logout(response: Response, session: str | None = Cookie(default=None)) -> dict:
    if session:
        with connect() as conn:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session,))
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"status": "ok"}


@router.get("/me")
def me(login: str = Depends(require_session)) -> dict:
    return {"login": login}
