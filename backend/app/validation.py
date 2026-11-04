"""Приём и проверка входного JSON товара (F004) — до любого вызова LLM.

Значения не «исправляются»: обрезаются только пробелы по краям, числа в specs
приводятся к строке как есть.
"""

import json
from dataclasses import dataclass, field

from .errors import ApiError

MAX_DESCRIPTION = 20_000
MAX_SPECS = 100
KNOWN_FIELDS = ("name", "manufacturer", "specs", "description")

FIELD_TITLES = {
    "manufacturer": "Производитель (manufacturer)",
    "specs": "Характеристики (specs)",
    "description": "Описание (description)",
}


@dataclass
class Product:
    name: str
    manufacturer: str = ""
    specs: dict[str, str] = field(default_factory=dict)
    description: str = ""

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "manufacturer": self.manufacturer,
            "specs": dict(self.specs),
            "description": self.description,
        }


@dataclass
class ValidatedInput:
    product: Product
    missing_fields: list[str]
    warnings: list[str]


def _invalid_field(name: str, message: str) -> ApiError:
    return ApiError(422, "invalid_field", message, {"field": name})


def _optional_str(data: dict, key: str) -> str:
    value = data.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise _invalid_field(key, f"Поле {key} должно быть строкой")
    return value.strip()


def _spec_value(key: str, value) -> str:
    if value is None:
        return ""
    # bool — подкласс int, но характеристикой-числом не является
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise _invalid_field(f"specs.{key}", f"Значение характеристики «{key}» должно быть строкой или числом")
    return value.strip() if isinstance(value, str) else str(value)


def parse_json(raw: bytes) -> object:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ApiError(400, "invalid_json", "Тело запроса не в кодировке UTF-8") from None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ApiError(
            400,
            "invalid_json",
            f"Некорректный JSON: строка {exc.lineno}, столбец {exc.colno}",
            {"line": exc.lineno, "column": exc.colno},
        ) from None


def validate_product(data: object) -> ValidatedInput:
    if not isinstance(data, dict):
        raise ApiError(422, "invalid_input", "Ожидается JSON-объект с полями name, manufacturer, specs, description")

    name = data.get("name")
    if name is not None and not isinstance(name, str):
        raise _invalid_field("name", "Поле name должно быть строкой")
    if name is None or not name.strip():
        raise ApiError(422, "missing_name", "Не задано название товара (name)", {"field": "name"})

    manufacturer = _optional_str(data, "manufacturer")
    description = _optional_str(data, "description")
    if len(description) > MAX_DESCRIPTION:
        raise ApiError(
            422, "too_large", f"Описание длиннее {MAX_DESCRIPTION} символов", {"field": "description"}
        )

    raw_specs = data.get("specs")
    if raw_specs is None:
        raw_specs = {}
    if not isinstance(raw_specs, dict):
        raise _invalid_field("specs", "Поле specs должно быть объектом «характеристика: значение»")
    if len(raw_specs) > MAX_SPECS:
        raise ApiError(422, "too_large", f"В specs больше {MAX_SPECS} характеристик", {"field": "specs"})

    missing: list[str] = []
    specs: dict[str, str] = {}
    empty_specs: list[str] = []
    for key, value in raw_specs.items():
        clean_key = str(key).strip()
        clean_value = _spec_value(clean_key, value)
        if clean_value:
            specs[clean_key] = clean_value
        else:
            empty_specs.append(clean_key)

    if not manufacturer:
        missing.append(FIELD_TITLES["manufacturer"])
    if not specs:
        missing.append(FIELD_TITLES["specs"])
    missing.extend(f"Характеристика «{key}» (specs.{key})" for key in empty_specs)
    if not description:
        missing.append(FIELD_TITLES["description"])

    warnings = [f"Поле {key} не используется" for key in data if key not in KNOWN_FIELDS]

    product = Product(name=name.strip(), manufacturer=manufacturer, specs=specs, description=description)
    return ValidatedInput(product=product, missing_fields=missing, warnings=warnings)


def validate_body(raw: bytes) -> ValidatedInput:
    return validate_product(parse_json(raw))
