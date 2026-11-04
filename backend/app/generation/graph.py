"""Граф генерации LangGraph: generate → check → (один повтор generate) → assemble."""

from typing import Any, TypedDict

import openai
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from ..errors import ApiError
from ..validation import ValidatedInput
from . import checks, llm
from .markdown import build_markdown
from .prompt import SYSTEM_PROMPT, retry_message, user_message
from .schema import NO_DATA, Card, GenerateResponse, KeySpec, ModelCard

MAX_ATTEMPTS = 2  # первый ответ + один повтор
SCHEMA_VIOLATION = "Ответ модели не соответствует схеме карточки"


class GenerationState(TypedDict, total=False):
    product: dict
    input_missing: list[str]
    input_warnings: list[str]
    card: ModelCard | None
    violations: list[str]
    attempts: int
    response: dict[str, Any]


def _generate(state: GenerationState, generator: llm.CardGenerator) -> GenerationState:
    messages = [SystemMessage(SYSTEM_PROMPT), HumanMessage(user_message(state["product"]))]
    if state.get("attempts", 0) > 0 and state.get("violations"):
        previous = state["card"].model_dump() if state.get("card") is not None else None
        messages.append(HumanMessage(retry_message(state["violations"], previous)))
    try:
        card = generator(messages)
        if not isinstance(card, ModelCard):
            card = ModelCard.model_validate(card)
    except (OutputParserException, ValidationError, *llm.SCHEMA_ERRORS):
        card = None
    return {"card": card, "attempts": state.get("attempts", 0) + 1}


def _check(state: GenerationState) -> GenerationState:
    card = state.get("card")
    if card is None:
        return {"violations": [SCHEMA_VIOLATION]}
    return {"violations": checks.find_violations(card, state["product"])}


def _route_after_check(state: GenerationState) -> str:
    if state.get("violations") and state.get("attempts", 0) < MAX_ATTEMPTS:
        return "generate"
    return "assemble"


def _assemble(state: GenerationState) -> GenerationState:
    model_card = state.get("card")
    if model_card is None:
        raise ApiError(502, "llm_bad_response", "Модель вернула некорректный ответ")

    verified = checks.verify_specs(model_card, state["product"])
    card = Card(
        seo_title=model_card.seo_title,
        seo_description=model_card.seo_description,
        key_specs=[KeySpec(name=s.name, value=s.value, verified=v) for s, v in zip(model_card.key_specs, verified)],
        search_queries=model_card.search_queries,
        commercial=model_card.commercial,
    )

    missing = list(state.get("input_missing", []))
    for spec in card.key_specs:
        item = f"{spec.name} (нет во входных данных)"
        if spec.value == NO_DATA and item not in missing:
            missing.append(item)

    warnings = list(state.get("input_warnings", []))
    values = {s.name: s.value for s in card.key_specs}
    warnings += [
        f"противоречие в данных: {p}"
        for p in model_card.data_conflicts
        if not checks.same_value_parts(values.get(p, ""))  # одно значение в разном написании — не противоречие
    ]
    warnings += state.get("violations", [])

    response = GenerateResponse(
        card=card, missing_fields=missing, warnings=warnings, markdown=build_markdown(card, missing, warnings)
    )
    return {"response": response.model_dump()}


def build_graph(generator: llm.CardGenerator):
    graph = StateGraph(GenerationState)
    graph.add_node("generate", lambda state: _generate(state, generator))
    graph.add_node("check", _check)
    graph.add_node("assemble", _assemble)
    graph.add_edge(START, "generate")
    graph.add_edge("generate", "check")
    graph.add_conditional_edges("check", _route_after_check, {"generate": "generate", "assemble": "assemble"})
    graph.add_edge("assemble", END)
    return graph.compile()


def run_generation(validated: ValidatedInput) -> dict:
    generator = llm.make_generator()
    graph = build_graph(generator)
    try:
        final = graph.invoke(
            {
                "product": validated.product.as_dict(),
                "input_missing": validated.missing_fields,
                "input_warnings": validated.warnings,
                "attempts": 0,
                "violations": [],
            },
            {"run_name": "generate_card"},
        )
    except openai.OpenAIError as exc:
        # Трасса в Phoenix к этому моменту уже закрыта со статусом ошибки (F006)
        raise llm.map_openai_error(exc) from None
    return final["response"]
