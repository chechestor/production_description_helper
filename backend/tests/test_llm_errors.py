"""F008: ошибки OpenAI API → понятный ответ. Исключения SDK замоканы, сеть не нужна."""

import dataclasses
import logging

import httpx2
import openai
import pytest
from langchain_core.exceptions import OutputParserException

from app import config
from app.generation import llm

TEST_KEY = "sk-test-NOT-A-REAL-KEY-123"
PRODUCT = {"name": "Манометр ТМ-210", "manufacturer": "РОСМА", "specs": {"Класс точности": "2.5"}}
REQUEST = httpx2.Request("POST", "https://api.openai.com/v1/chat/completions")


def status_error(cls, status: int):
    return cls(f"HTTP {status}", response=httpx2.Response(status, request=REQUEST), body=None)


@pytest.fixture
def raise_from_llm(auth_client, monkeypatch, settings):
    """Подменяет вызов модели исключением; ключ «задан», чтобы дойти до вызова."""
    monkeypatch.setattr(config, "settings", dataclasses.replace(settings, openai_api_key=TEST_KEY))

    def install(exc):
        calls = []

        def generator(messages):
            calls.append(messages)
            raise exc

        monkeypatch.setattr(llm, "make_generator", lambda: generator)
        return calls

    return install


@pytest.mark.parametrize(
    ("exc", "status", "code"),
    [
        (status_error(openai.AuthenticationError, 401), 502, "llm_auth_error"),
        (status_error(openai.PermissionDeniedError, 403), 502, "llm_auth_error"),
        (status_error(openai.RateLimitError, 429), 503, "llm_rate_limited"),
        (status_error(openai.APIStatusError, 503), 503, "llm_rate_limited"),
        (openai.APITimeoutError(request=REQUEST), 504, "llm_timeout"),
        (openai.APIConnectionError(request=REQUEST), 502, "llm_unavailable"),
        (status_error(openai.InternalServerError, 500), 502, "llm_unavailable"),
        (status_error(openai.BadRequestError, 400), 502, "llm_unavailable"),
    ],
)
def test_openai_errors(auth_client, raise_from_llm, caplog, exc, status, code):
    raise_from_llm(exc)
    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        response = auth_client.post("/api/generate", json=PRODUCT)

    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] == code
    assert "card" not in response.json()  # без заглушки вместо карточки
    assert "Traceback" not in response.text and TEST_KEY not in response.text

    lines = [r.getMessage() for r in caplog.records if "Ошибка LLM" in r.getMessage()]
    assert lines == [f"Ошибка LLM: code={code} type={type(exc).__name__}"]
    assert TEST_KEY not in caplog.text and "Манометр" not in caplog.text  # ни ключа, ни входа в логе

    # Сервер продолжает отвечать
    assert auth_client.get("/api/health").status_code == 200


def test_timeout_message_has_seconds(auth_client, raise_from_llm):
    raise_from_llm(openai.APITimeoutError(request=REQUEST))
    response = auth_client.post("/api/generate", json=PRODUCT)
    assert f"{config.settings.llm_timeout} с" in response.json()["error"]["message"]


def test_no_key(auth_client):
    response = auth_client.post("/api/generate", json=PRODUCT)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "llm_not_configured"


def test_bad_response_after_retry(auth_client, raise_from_llm):
    calls = raise_from_llm(OutputParserException("not json"))
    response = auth_client.post("/api/generate", json=PRODUCT)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "llm_bad_response"
    assert len(calls) == 2  # первый ответ + один повтор


def test_length_finish_is_schema_error(auth_client, raise_from_llm):
    from types import SimpleNamespace

    calls = raise_from_llm(openai.LengthFinishReasonError(completion=SimpleNamespace(usage=None)))
    response = auth_client.post("/api/generate", json=PRODUCT)
    assert response.json()["error"]["code"] == "llm_bad_response"
    assert len(calls) == 2
