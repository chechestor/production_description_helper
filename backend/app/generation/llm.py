"""Вызов OpenAI через LangChain (ChatOpenAI + structured output) и разбор ошибок API (F008)."""

import logging
from collections.abc import Callable

import openai
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from .. import config
from ..errors import ApiError
from .schema import ModelCard

CardGenerator = Callable[[list[BaseMessage]], ModelCard]

logger = logging.getLogger("uvicorn.error")

# Ответ не по схеме: обрабатывается как нарушение схемы (повтор, затем llm_bad_response)
SCHEMA_ERRORS = (openai.LengthFinishReasonError, openai.ContentFilterFinishReasonError)


def map_openai_error(exc: openai.OpenAIError) -> ApiError:
    """Исключение SDK OpenAI → ответ API. В лог — одна строка: код и тип исключения."""
    if isinstance(exc, openai.APITimeoutError):
        error = ApiError(504, "llm_timeout", f"Модель не ответила за {config.settings.llm_timeout} с")
    elif isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
        error = ApiError(502, "llm_auth_error", "Ключ API OpenAI отклонён")
    elif isinstance(exc, openai.RateLimitError) or (
        isinstance(exc, openai.APIStatusError) and exc.status_code in (503, 529)
    ):
        error = ApiError(503, "llm_rate_limited", "Лимит запросов к OpenAI или перегрузка, повторите позже")
    else:  # сеть, 5xx провайдера, прочие ошибки SDK
        error = ApiError(502, "llm_unavailable", "Сервис LLM недоступен")
    logger.warning("Ошибка LLM: code=%s type=%s", error.code, type(exc).__name__)
    return error


def make_generator() -> CardGenerator:
    """Генератор карточки по сообщениям. Тесты подменяют эту функцию моком."""
    s = config.settings
    if not s.llm_configured:
        raise ApiError(503, "llm_not_configured", "Не задан ключ API OpenAI (OPENAI_API_KEY), см. README")
    llm = ChatOpenAI(
        model=s.llm_model,
        api_key=s.openai_api_key,
        timeout=s.llm_timeout,
        max_retries=1,
        temperature=0.2,
    )
    structured = llm.with_structured_output(ModelCard, method="json_schema", strict=True)
    return structured.invoke
