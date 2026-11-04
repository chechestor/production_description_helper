"""SQLite в папке data/: создание файла и таблиц при старте.

Существующие данные не трогаются (CREATE TABLE IF NOT EXISTS).
"""

import sqlite3
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,          -- случайный токен сессии
    login TEXT NOT NULL,
    created_at TEXT NOT NULL,     -- ISO 8601, UTC
    expires_at TEXT NOT NULL      -- ISO 8601, UTC
);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions (expires_at);
"""


def database_file() -> Path:
    """Путь к файлу БД; относительный путь считается от корня проекта."""
    path = Path(config.settings.database_path)
    return path if path.is_absolute() else config.PROJECT_ROOT / path


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(database_file())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> Path:
    path = database_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)
    conn.close()
    return path
