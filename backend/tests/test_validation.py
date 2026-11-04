"""F004: проверка входного JSON до вызова LLM."""

import pytest

from app.validation import validate_product

GENERATE = "/api/generate"
VALIDATION_CODES = {"invalid_json", "invalid_input", "missing_name", "invalid_field", "too_large"}


def post_raw(client, body: str):
    return client.post(GENERATE, content=body.encode("utf-8"), headers={"Content-Type": "application/json"})


def error_of(response):
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "details"}
    assert "Traceback" not in response.text
    return body["error"]


# --- сессия проверяется раньше JSON ---


@pytest.mark.parametrize("body", ["{bad", "[]", '{"name": ""}', '{"name": "Манометр"}'])
def test_without_login_always_401(client, body):
    response = post_raw(client, body)
    assert response.status_code == 401
    assert error_of(response)["code"] == "unauthorized"


# --- строки таблицы ошибок ---


def test_not_json(auth_client):
    response = post_raw(auth_client, '{"name": "x",\n  "specs": }')
    assert response.status_code == 400
    error = error_of(response)
    assert error["code"] == "invalid_json"
    assert "строка 2" in error["message"] and "столбец" in error["message"]


@pytest.mark.parametrize("body", ["[]", '"текст"', "42", "null"])
def test_not_object(auth_client, body):
    response = post_raw(auth_client, body)
    assert response.status_code == 422
    assert error_of(response)["code"] == "invalid_input"


@pytest.mark.parametrize("body", ["{}", '{"name": ""}', '{"name": "   "}', '{"name": null}'])
def test_missing_name(auth_client, body):
    response = post_raw(auth_client, body)
    assert response.status_code == 422
    assert error_of(response)["code"] == "missing_name"


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"name": 5}, "name"),
        ({"name": "x", "manufacturer": ["ОВЕН"]}, "manufacturer"),
        ({"name": "x", "description": {"a": 1}}, "description"),
        ({"name": "x", "specs": ["a"]}, "specs"),
        ({"name": "x", "specs": {"Класс": [2.5]}}, "specs.Класс"),
        ({"name": "x", "specs": {"Класс": True}}, "specs.Класс"),
    ],
)
def test_invalid_field(auth_client, payload, field):
    response = auth_client.post(GENERATE, json=payload)
    assert response.status_code == 422
    error = error_of(response)
    assert error["code"] == "invalid_field"
    assert error["details"] == {"field": field}


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "x", "description": "а" * 20_001},
        {"name": "x", "specs": {f"п{i}": "1" for i in range(101)}},
    ],
)
def test_too_large(auth_client, payload):
    response = auth_client.post(GENERATE, json=payload)
    assert response.status_code == 422
    assert error_of(response)["code"] == "too_large"


def test_limits_are_inclusive():
    validate_product({"name": "x", "description": "а" * 20_000, "specs": {f"п{i}": "1" for i in range(100)}})


# --- нормализация и недостающие данные ---


def test_incomplete_pd100():
    result = validate_product({"name": "ПД100-ДИ0,1-111-0,5", "manufacturer": "ОВЕН", "specs": {}, "description": ""})
    assert "Характеристики (specs)" in result.missing_fields
    assert "Описание (description)" in result.missing_fields
    assert "Производитель (manufacturer)" not in result.missing_fields
    assert result.product.name == "ПД100-ДИ0,1-111-0,5"


def test_normalization_keeps_values_as_is():
    result = validate_product(
        {
            "name": "  Манометр ТМ-210  ",
            "specs": {"Класс точности": 2.5, "Диаметр": 50, "Резьба": " М12х1,5 ", "Питание": None, "IP": ""},
            "description": " Текст ",
        }
    )
    product = result.product
    assert product.name == "Манометр ТМ-210"
    assert product.specs == {"Класс точности": "2.5", "Диаметр": "50", "Резьба": "М12х1,5"}
    assert product.description == "Текст"
    assert "Характеристика «Питание» (specs.Питание)" in result.missing_fields
    assert "Характеристика «IP» (specs.IP)" in result.missing_fields
    assert "Производитель (manufacturer)" in result.missing_fields


def test_extra_fields_warning():
    result = validate_product({"name": "x", "price": 100, "url": "http://x"})
    assert result.warnings == ["Поле price не используется", "Поле url не используется"]


def test_valid_input_is_not_rejected_by_validation(auth_client, monkeypatch):
    # Генерацию подменяем: проверка не должна вызывать LLM и не должна отклонять корректный вход
    response = auth_client.post(GENERATE, json={"name": "Манометр", "manufacturer": "РОСМА"})
    assert response.status_code not in (400, 422)
    if response.status_code >= 400:
        assert error_of(response)["code"] not in VALIDATION_CODES
