"""Схемы карточки: что возвращает модель и что отдаёт API."""

from pydantic import BaseModel, Field

NO_DATA = "данных нет"


class ModelKeySpec(BaseModel):
    name: str = Field(description="Название характеристики")
    value: str = Field(description=f"Значение дословно из входных данных или «{NO_DATA}»")


class Commercial(BaseModel):
    audience: list[str] = Field(description="Кому подходит прибор: 2–4 пункта")
    tasks: list[str] = Field(description="Какие задачи решает: 2–4 пункта")


class ModelCard(BaseModel):
    """Ответ модели (structured output)."""

    seo_title: str = Field(description="SEO-заголовок, не длиннее 70 символов с пробелами")
    seo_description: str = Field(description="SEO-описание, 800–1200 символов с пробелами")
    key_specs: list[ModelKeySpec] = Field(description="Ключевые характеристики")
    search_queries: list[str] = Field(description="3–5 поисковых запросов")
    commercial: Commercial
    data_conflicts: list[str] = Field(
        description="Параметры, для которых во входных данных указаны разные значения; пустой список, если таких нет"
    )


class KeySpec(BaseModel):
    name: str
    value: str
    verified: bool


class Card(BaseModel):
    """Карточка в ответе API."""

    seo_title: str
    seo_description: str
    key_specs: list[KeySpec]
    search_queries: list[str]
    commercial: Commercial


class GenerateResponse(BaseModel):
    card: Card
    missing_fields: list[str]
    warnings: list[str]
    markdown: str
