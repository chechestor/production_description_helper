"""Трассы LangChain/LangGraph в Phoenix через OpenTelemetry (OpenInference).

Пустой PHOENIX_COLLECTOR_ENDPOINT отключает трассировку (так работают тесты).
Если Phoenix недоступен, экспортёр в фоне пишет ошибку в лог, а запросы API
работают как обычно: отправка трасс не влияет на ответ.
"""

import logging

from . import config

logger = logging.getLogger("uvicorn.error")

_tracer_provider = None


def setup_tracing():
    """Регистрирует экспорт трасс в Phoenix и инструментирует LangChain (один раз)."""
    global _tracer_provider
    if _tracer_provider is not None:
        return _tracer_provider

    s = config.settings
    if not s.phoenix_collector_endpoint:
        logger.info("Трассировка в Phoenix отключена: PHOENIX_COLLECTOR_ENDPOINT пуст")
        return None

    from openinference.instrumentation.langchain import LangChainInstrumentor
    from phoenix.otel import register

    endpoint = s.phoenix_collector_endpoint.rstrip("/") + "/v1/traces"
    _tracer_provider = register(
        endpoint=endpoint,
        project_name=s.phoenix_project_name,
        protocol="http/protobuf",
        batch=True,
        verbose=False,
    )
    LangChainInstrumentor().instrument(tracer_provider=_tracer_provider)
    logger.info("Трассы LangChain/LangGraph: %s, проект %s", endpoint, s.phoenix_project_name)
    return _tracer_provider


def shutdown_tracing() -> None:
    if _tracer_provider is not None:
        try:
            _tracer_provider.shutdown()
        except Exception:  # noqa: BLE001 — выход сервера не должен падать из-за Phoenix
            logger.warning("Не удалось корректно закрыть экспорт трасс")
