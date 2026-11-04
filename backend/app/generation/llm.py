"""Вызов OpenAI через LangChain (ChatOpenAI + structured output)."""

from collections.abc import Callable

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from .. import config
from ..errors import ApiError
from .schema import ModelCard

CardGenerator = Callable[[list[BaseMessage]], ModelCard]


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
