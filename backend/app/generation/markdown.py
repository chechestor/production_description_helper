"""Markdown карточки собирается кодом из card, а не моделью."""

from .schema import NO_DATA, Card


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def build_markdown(card: Card, missing_fields: list[str], warnings: list[str]) -> str:
    parts = [
        "## SEO-заголовок",
        "",
        card.seo_title,
        "",
        "## SEO-описание",
        "",
        card.seo_description,
        "",
        "## Ключевые характеристики",
        "",
        "| Характеристика | Значение |",
        "|---|---|",
    ]
    for spec in card.key_specs:
        value = _cell(spec.value)
        if spec.value != NO_DATA and not spec.verified:
            value += " ⚠ не найдено во входных данных"
        parts.append(f"| {_cell(spec.name)} | {value} |")
    parts += ["", "## Поисковые запросы", ""]
    parts += [f"- {q}" for q in card.search_queries]
    parts += ["", "## Для менеджера", "", "**Кому подходит:**", ""]
    parts += [f"- {a}" for a in card.commercial.audience]
    parts += ["", "**Какие задачи решает:**", ""]
    parts += [f"- {t}" for t in card.commercial.tasks]
    if missing_fields:
        parts += ["", "## Недостающие данные", ""]
        parts += [f"- {m}" for m in missing_fields]
    if warnings:
        parts += ["", "## Предупреждения", ""]
        parts += [f"- {w}" for w in warnings]
    return "\n".join(parts) + "\n"
