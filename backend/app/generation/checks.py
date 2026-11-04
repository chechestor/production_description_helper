"""Проверки ответа модели кодом (узел check графа).

F005: базовая сверка значений key_specs со входом. Полный набор проверок a–e — F007.
"""

from .schema import NO_DATA, ModelCard


def input_text(product: dict) -> str:
    specs = product.get("specs") or {}
    parts = [product.get("name", ""), product.get("manufacturer", "")]
    parts += [f"{k}: {v}" for k, v in specs.items()]
    parts.append(product.get("description", ""))
    return "\n".join(parts)


def value_found(value: str, product: dict) -> bool:
    return value.strip().lower() in input_text(product).lower()


def verify_specs(card: ModelCard, product: dict) -> list[bool]:
    return [spec.value == NO_DATA or value_found(spec.value, product) for spec in card.key_specs]


def find_violations(card: ModelCard, product: dict) -> list[str]:
    return []
