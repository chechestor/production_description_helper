"""Общие фикстуры: тесты не зависят от .env, не пишут в data/ и не ходят в сеть
(кроме явного режима --inputs=feed)."""

import dataclasses
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Ссылка на YML-фид из ТЗ (.task/ не в git, поэтому ссылка здесь)
DEFAULT_FEED_URL = "https://www.souz-pribor.ru/yml/any/feed.xml"


def pytest_addoption(parser):
    group = parser.getgroup("inputs", "Тестовые входы F004")
    group.addoption(
        "--inputs",
        choices=("local", "feed"),
        default="local",
        help="local — *.json из --inputs-dir; feed — офферы из YML-фида (нужна сеть)",
    )
    group.addoption("--inputs-dir", default=str(PROJECT_ROOT / "examples" / "input"), help="папка с *.json")
    group.addoption("--feed-url", default=DEFAULT_FEED_URL, help="ссылка на YML-фид")
    group.addoption("--offer-ids", default="170353,189862", help="id офферов через запятую")


@pytest.fixture
def settings(tmp_path, monkeypatch):
    """Настройки тестов: без ключа OpenAI, SQLite во временной папке, вход user/user."""
    test_settings = dataclasses.replace(
        config.settings,
        openai_api_key="",
        database_path=str(tmp_path / "app.db"),
        auth_login="user",
        auth_password="user",
        phoenix_collector_endpoint="",  # трассировка в тестах отключена
    )
    monkeypatch.setattr(config, "settings", test_settings)
    return test_settings


@pytest.fixture
def client(settings):
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_client(client):
    """Клиент с выполненным входом (cookie session)."""
    response = client.post("/api/login", json={"login": "user", "password": "user"})
    assert response.status_code == 200
    return client
