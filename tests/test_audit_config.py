"""Offline infrastructure checks: no model requests."""
import json

import pytest

from rehearsal.audit import EventLog
from rehearsal.config import settings


def test_secrets_redacted_but_usage_preserved(tmp_path):
    log = EventLog(tmp_path, secrets=("private-value",))
    log.emit("failure", api_key="hidden", message="error private-value", input_tokens=42)
    log.artifact("output.json", {"authorization": "Bearer hidden", "reply": "private-value"})
    content = (log.directory / "events.jsonl").read_text(encoding="utf-8")
    assert "private-value" not in content
    assert "hidden" not in content
    assert json.loads(content)["data"]["input_tokens"] == 42
    assert "private-value" not in (log.directory / "output.json").read_text()


def test_missing_config_is_explicit(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        settings("groq")


def test_compatible_provider_requires_safe_url(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "test-model")
    monkeypatch.setenv("GROQ_BASE_URL", "https://key@example.com/v1")
    with pytest.raises(ValueError, match="HTTPS"):
        settings("groq")
