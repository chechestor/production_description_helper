"""Общие фикстуры: тесты не зависят от .env, не пишут в data/ и не ходят в сеть."""

import dataclasses

import pytest
from fastapi.testclient import TestClient

from app import config


@pytest.fixture
def settings(tmp_path, monkeypatch):
    """Настройки тестов: без ключа OpenAI, SQLite во временной папке."""
    test_settings = dataclasses.replace(
        config.settings,
        openai_api_key="",
        database_path=str(tmp_path / "app.db"),
    )
    monkeypatch.setattr(config, "settings", test_settings)
    return test_settings


@pytest.fixture
def client(settings):
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
