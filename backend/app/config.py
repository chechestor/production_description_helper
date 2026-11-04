"""Настройки приложения из переменных окружения и файла .env в корне проекта.

Переменные окружения имеют приоритет над .env. Значение OPENAI_API_KEY нигде
не печатается: в repr настроек оно скрыто, наружу отдаётся только признак
«задан / не задан».
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# override=False: значения из окружения (в том числе env_file в Docker) важнее .env
load_dotenv(PROJECT_ROOT / ".env", override=False)


def _str(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value is not None else default


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"Переменная {name} должна быть целым числом") from exc


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = field(repr=False)
    llm_model: str
    llm_timeout: int
    phoenix_collector_endpoint: str
    phoenix_project_name: str
    database_path: str
    session_ttl_hours: int
    auth_login: str
    auth_password: str = field(repr=False)

    @property
    def llm_configured(self) -> bool:
        return bool(self.openai_api_key)


def load_settings() -> Settings:
    return Settings(
        openai_api_key=_str("OPENAI_API_KEY", ""),
        llm_model=_str("LLM_MODEL", "gpt-4.1-mini"),
        llm_timeout=_int("LLM_TIMEOUT", 60),
        phoenix_collector_endpoint=_str("PHOENIX_COLLECTOR_ENDPOINT", "http://phoenix:6006"),
        phoenix_project_name=_str("PHOENIX_PROJECT_NAME", "product-description-helper"),
        database_path=_str("DATABASE_PATH", "data/app.db"),
        session_ttl_hours=_int("SESSION_TTL_HOURS", 168),
        auth_login=_str("AUTH_LOGIN", ""),
        auth_password=_str("AUTH_PASSWORD", ""),
    )


# AUTH_LOGIN и AUTH_PASSWORD без значений по умолчанию в коде: задаются только в .env (F003).
settings = load_settings()
