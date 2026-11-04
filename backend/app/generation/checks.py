"""Проверки ответа модели кодом (F007) — узел check графа.

a) seo_title ≤ 70 символов; b) seo_description 800–1200 символов;
c) 3–5 непустых поисковых запросов; d) значения key_specs найдены во входе;
e) числа из seo_description найдены во входе.

Вход для сверки — name, manufacturer, specs, description. Сверка после нормализации:
регистр, пробелы, ×/х/x, похожие кириллические и латинские буквы, десятичные «,» и «.».
Текст модели код не правит: нарушения уходят в повтор, затем в warnings.
"""

import re

from .schema import NO_DATA, ModelCard

TITLE_MAX = 70
DESCRIPTION_MIN, DESCRIPTION_MAX = 800, 1200
QUERIES_MIN, QUERIES_MAX = 3, 5

# Похожие кириллические буквы → латинские (после перевода в нижний регистр)
_LOOKALIKES = str.maketrans(
    {"а": "a", "в": "b", "е": "e", "к": "k", "м": "m", "н": "h", "о": "o", "р": "p", "с": "c", "т": "t", "х": "x",
     "×": "x", ",": "."}
)
_SPACES = re.compile(r"\s+")
# Разделители частей значения — только с пробелом после, чтобы не резать «1,5» и «G1/4»
_PART_SEPARATORS = re.compile(r", |; | / ")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def normalize(text: str) -> str:
    return _SPACES.sub(" ", text.lower().translate(_LOOKALIKES)).strip()


def input_text(product: dict) -> str:
    specs = product.get("specs") or {}
    parts = [product.get("name", ""), product.get("manufacturer", "")]
    parts += [f"{k}: {v}" for k, v in specs.items()]
    parts.append(product.get("description", ""))
    return normalize("\n".join(parts))


def value_found(value: str, haystack: str) -> bool:
    """d): каждая часть значения встречается во входе."""
    parts = [p for p in (normalize(x) for x in _PART_SEPARATORS.split(value)) if p]
    return bool(parts) and all(p in haystack for p in parts)


def same_value_parts(value: str) -> bool:
    """Все варианты значения через « / » после нормализации совпадают («2.5 / 2,5», «IP-40 / IP40»)."""
    variants = {normalize(v).replace("-", "") for v in value.split(" / ") if v.strip()}
    return len(variants) == 1 and " / " in value


def number_found(number: str, haystack: str) -> bool:
    """e): число встречается во входе как отдельное число, а не часть другого."""
    n = re.escape(normalize(number))
    return re.search(rf"(?<![\d.]){n}(?!\d|\.\d)", haystack) is not None


def verify_specs(card: ModelCard, product: dict) -> list[bool]:
    haystack = input_text(product)
    return [spec.value == NO_DATA or value_found(spec.value, haystack) for spec in card.key_specs]


def find_violations(card: ModelCard, product: dict) -> list[str]:
    haystack = input_text(product)
    violations: list[str] = []

    title_len = len(card.seo_title)
    if title_len > TITLE_MAX:
        violations.append(f"SEO-заголовок {title_len} символов, нужно не больше {TITLE_MAX}")

    desc_len = len(card.seo_description)
    if not DESCRIPTION_MIN <= desc_len <= DESCRIPTION_MAX:
        violations.append(f"SEO-описание {desc_len} символов, нужно {DESCRIPTION_MIN}–{DESCRIPTION_MAX}")

    queries = card.search_queries
    if not QUERIES_MIN <= len(queries) <= QUERIES_MAX:
        violations.append(f"Поисковых запросов {len(queries)}, нужно {QUERIES_MIN}–{QUERIES_MAX}")
    if any(not q.strip() for q in queries):
        violations.append("Есть пустой поисковый запрос")

    for spec in card.key_specs:
        if spec.value != NO_DATA and not value_found(spec.value, haystack):
            violations.append(
                f"Значение «{spec.value}» характеристики «{spec.name}» не найдено во входных данных дословно"
            )

    seen: set[str] = set()
    for number in _NUMBER.findall(card.seo_description):
        if number not in seen and not number_found(number, haystack):
            violations.append(f"Число {number} в описании не найдено во входных данных")
        seen.add(number)

    return violations
