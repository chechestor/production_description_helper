"""F004: прогон тестовых входов через проверку.

pytest                      — входы из examples/input/ (или --inputs-dir)
pytest --inputs=feed        — офферы из YML-фида (--feed-url, --offer-ids); без сети — skip
"""

import json
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from app.validation import validate_product


def _local_inputs(config) -> list[tuple[str, dict]]:
    folder = Path(config.getoption("--inputs-dir"))
    return [(f.name, json.loads(f.read_text(encoding="utf-8"))) for f in sorted(folder.glob("*.json"))]


def _feed_inputs(config) -> list[tuple[str, dict]]:
    url = config.getoption("--feed-url")
    wanted = [i.strip() for i in config.getoption("--offer-ids").split(",") if i.strip()]
    found: dict[str, dict] = {}
    try:
        # Сайт отвечает 403 на User-Agent «Python-urllib», поэтому нейтральный заголовок клиента
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; pdh-tests/1.0)"})
        with urllib.request.urlopen(req, timeout=60) as response:
            for _, element in ET.iterparse(response, events=("end",)):
                if element.tag != "offer":
                    continue
                offer_id = element.get("id")
                if offer_id in wanted:
                    # В фиде есть только название и производитель
                    found[offer_id] = {
                        "name": (element.findtext("name") or "").strip(),
                        "manufacturer": (element.findtext("vendor") or "").strip(),
                        "specs": {},
                        "description": "",
                    }
                    if len(found) == len(wanted):
                        break
                element.clear()
    except (urllib.error.URLError, TimeoutError, OSError, ET.ParseError) as exc:
        pytest.skip(f"Фид недоступен: {exc}")
    missing = [i for i in wanted if i not in found]
    if missing:
        pytest.skip(f"В фиде нет офферов: {', '.join(missing)}")
    return [(f"offer-{i}", found[i]) for i in wanted]


def test_inputs_pass_validation(request):
    mode = request.config.getoption("--inputs")
    inputs = _feed_inputs(request.config) if mode == "feed" else _local_inputs(request.config)
    assert inputs, "Нет тестовых входов"

    for label, data in inputs:
        result = validate_product(data)  # ошибка проверки — исключение ApiError
        assert result.product.name, label
        if mode == "feed":
            assert "Характеристики (specs)" in result.missing_fields, label
            assert "Описание (description)" in result.missing_fields, label
