"""Offline flow simulations; these do not assess real model quality."""
import asyncio
import json

import pytest

from rehearsal.__main__ import process, read_messages, ROOT
from rehearsal.audit import EventLog
from rehearsal.contracts import Draft


def test_original_five_messages():
    assert read_messages(ROOT / "messages.txt") == [
        "Как получить справку о месте учёбы?",
        "В столовой очередь, еда холодная.",
        "Хочу записаться на консультацию завтра.",
        "Пропал Wi‑Fi в корпусе B.",
        "Где парковка для гостей?",
    ]


def test_empty_input_is_not_a_success(tmp_path):
    path = tmp_path / "empty.txt"
    path.write_text("\n", encoding="utf-8")
    with pytest.raises(ValueError, match="пуст"):
        read_messages(path)


def test_partial_failure_preserves_other_messages(tmp_path):
    class ScriptedGateway:
        async def generate(self, instructions, payload, output_type, stage):
            if payload["message"] == "fail":
                raise RuntimeError("private-token")
            return Draft(category="другое", reply="Тестовый черновик")

    log = EventLog(tmp_path)
    results = asyncio.run(process(["ok", "fail", "ok-again"], ScriptedGateway(), log))
    assert results[1].baseline is None
    assert results[1].errors == {"baseline": "RuntimeError"}
    assert results[2].baseline is not None
    saved = json.loads((log.directory / "results.json").read_text(encoding="utf-8"))
    assert len(saved) == 3
    assert "private-token" not in (log.directory / "events.jsonl").read_text()
