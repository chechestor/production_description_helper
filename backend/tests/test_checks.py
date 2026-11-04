"""F007: проверки ответа модели кодом и один повтор. LLM замокана."""

import json

import pytest

from app.errors import ApiError
from app.generation import checks, graph, llm
from app.generation.schema import ModelCard
from app.validation import validate_product
from tests.conftest import PROJECT_ROOT

GOOD_DESCRIPTION = ("Сварочный манометр применяется в баллонных редукторах и регуляторах для контроля давления. " * 10)[:900]


def tm210() -> dict:
    data = json.loads((PROJECT_ROOT / "examples" / "input" / "tm-210.json").read_text(encoding="utf-8"))
    return validate_product(data).product.as_dict()


def make_card(**overrides) -> ModelCard:
    card = {
        "seo_title": "Манометр сварочный ТМ-210 РОСМА",
        "seo_description": GOOD_DESCRIPTION,
        "key_specs": [
            {"name": "Класс точности", "value": "2.5"},
            {"name": "Резьба присоединения", "value": "М12х1,5, G1/4 / M12×1,5"},
            {"name": "Питание", "value": "данных нет"},
        ],
        "search_queries": ["манометр ТМ-210", "манометр сварочный", "манометр РОСМА"],
        "commercial": {"audience": ["сварочные посты", "газовые участки"], "tasks": ["контроль давления", "редукторы"]},
        "data_conflicts": ["Резьба присоединения"],
    }
    card.update(overrides)
    return ModelCard.model_validate(card)


class FakeGenerator:
    """Мок модели: отдаёт ответы по очереди и считает вызовы."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls: list[list] = []

    def __call__(self, messages):
        self.calls.append(messages)
        answer = self.answers[min(len(self.calls), len(self.answers)) - 1]
        if isinstance(answer, Exception):
            raise answer
        return answer


def run(generator, product=None) -> dict:
    product = product or tm210()
    state = {"product": product, "input_missing": [], "input_warnings": [], "attempts": 0, "violations": []}
    return graph.build_graph(generator).invoke(state)["response"]


# --- каждая проверка a–e ловит нарушение ---


def test_good_card_has_no_violations():
    assert checks.find_violations(make_card(), tm210()) == []


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"seo_title": "М" * 71}, "SEO-заголовок 71 символов"),  # a
        ({"seo_description": "а" * 799}, "SEO-описание 799 символов"),  # b
        ({"seo_description": "а" * 1201}, "SEO-описание 1201 символов"),  # b
        ({"search_queries": ["a", "b"]}, "Поисковых запросов 2"),  # c
        ({"search_queries": ["a", "b", "c", "d", "e", "f"]}, "Поисковых запросов 6"),  # c
        ({"search_queries": ["a", " ", "c"]}, "пустой поисковый запрос"),  # c
        ({"key_specs": [{"name": "Класс точности", "value": "1.0"}]}, "Значение «1.0»"),  # d
        ({"seo_description": GOOD_DESCRIPTION[:880] + " давление 16 МПа."}, "Число 16"),  # e
    ],
)
def test_each_check_catches_violation(overrides, expected):
    violations = checks.find_violations(make_card(**overrides), tm210())
    assert any(expected in v for v in violations), violations


def test_cyrillic_and_latin_thread_match():
    product = tm210()
    haystack = checks.input_text(product)
    assert checks.value_found("M12×1,5", haystack)  # латиница и ×
    assert checks.value_found("М12х1,5", haystack)  # кириллица и х
    assert checks.value_found("М12х1,5, G1/4 / M12×1,5", haystack)  # противоречие по правилу 3 F005
    assert not checks.value_found("М20х1,5", haystack)


def test_decimal_comma_and_dot_are_equal():
    haystack = checks.input_text(tm210())
    assert checks.value_found("2,5", haystack) and checks.value_found("2.5", haystack)


def test_number_from_name_is_not_flagged():
    card = make_card(seo_description=GOOD_DESCRIPTION[:880] + " Модель ТМ-210.")
    assert checks.find_violations(card, tm210()) == []


def test_number_must_match_whole():
    haystack = checks.input_text(tm210())
    assert checks.number_found("50", haystack)
    assert not checks.number_found("5", haystack)  # «5» есть только внутри «1,5», «2,5», «50»


# --- повтор ---


def test_contradiction_value_is_verified_without_retry():
    generator = FakeGenerator(make_card())
    response = run(generator)
    assert len(generator.calls) == 1
    thread = next(s for s in response["card"]["key_specs"] if s["name"] == "Резьба присоединения")
    assert thread["verified"] is True
    assert "противоречие в данных: Резьба присоединения" in response["warnings"]


def test_retry_success_gives_no_check_warnings():
    generator = FakeGenerator(make_card(seo_title="М" * 80), make_card())
    response = run(generator)
    assert len(generator.calls) == 2
    retry_prompt = generator.calls[1][-1].content
    assert "SEO-заголовок 80 символов" in retry_prompt
    assert response["warnings"] == ["противоречие в данных: Резьба присоединения"]


def test_retry_failure_puts_violation_into_warnings():
    bad = make_card(seo_description="а" * 1312)
    generator = FakeGenerator(bad, bad, bad)
    response = run(generator)
    assert len(generator.calls) == 2  # не больше одного повтора
    assert "SEO-описание 1312 символов, нужно 800–1200" in response["warnings"]


def test_unverified_value_marked_and_warned():
    bad = make_card(key_specs=[{"name": "Класс точности", "value": "1.0"}])
    generator = FakeGenerator(bad, bad)
    response = run(generator)
    assert len(generator.calls) == 2
    assert response["card"]["key_specs"][0]["verified"] is False
    assert any("Значение «1.0»" in w for w in response["warnings"])


def test_schema_error_retries_then_succeeds():
    from pydantic import ValidationError

    broken = ValidationError.from_exception_data("ModelCard", [])
    generator = FakeGenerator(broken, make_card())
    response = run(generator)
    assert len(generator.calls) == 2
    assert response["card"]["seo_title"]


def test_schema_error_twice_is_bad_response():
    from langchain_core.exceptions import OutputParserException

    generator = FakeGenerator(OutputParserException("bad json"), OutputParserException("bad json"))
    with pytest.raises(ApiError) as exc:
        run(generator)
    assert exc.value.code == "llm_bad_response" and exc.value.status == 502
    assert len(generator.calls) == 2


# --- через API ---


def test_generate_endpoint_with_mocked_llm(auth_client, monkeypatch):
    generator = FakeGenerator(make_card())
    monkeypatch.setattr(llm, "make_generator", lambda: generator)
    data = json.loads((PROJECT_ROOT / "examples" / "input" / "tm-210.json").read_text(encoding="utf-8"))
    response = auth_client.post("/api/generate", json=data)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"card", "missing_fields", "warnings", "markdown"}
    assert "Питание (нет во входных данных)" in body["missing_fields"]
    assert "## Ключевые характеристики" in body["markdown"]
    assert len(generator.calls) == 1


def test_generate_without_key_is_503(auth_client):
    response = auth_client.post("/api/generate", json={"name": "Манометр"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "llm_not_configured"
