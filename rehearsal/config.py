"""Explicit provider configuration; never fall back to mock or a different model."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    provider: str
    model: str
    api_key: str = field(repr=False)
    base_url: str | None = None


def settings(provider: str, env_file: Path | None = None) -> Settings:
    if env_file is not None:
        if not env_file.is_file():
            raise ValueError("Указанный файл окружения не найден")
        load_dotenv(env_file, override=False)
    prefix = provider.upper()
    key = os.environ.get(f"{prefix}_API_KEY", "").strip()
    model = os.environ.get(f"{prefix}_MODEL", "").strip()
    base_url = os.environ.get(f"{prefix}_BASE_URL", "").strip() or None
    if not key or not model:
        raise ValueError(f"Нужно задать {prefix}_API_KEY и {prefix}_MODEL")
    if provider != "openai" and base_url is None:
        raise ValueError(f"Нужно задать {prefix}_BASE_URL")
    if base_url:
        url = urlsplit(base_url)
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("BASE_URL должен быть HTTPS URL без учётных данных и параметров")
    return Settings(provider, model, key, base_url)
