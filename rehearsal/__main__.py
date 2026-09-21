"""CLI for the real baseline; checker semantics are awaiting joint specification."""
import argparse
import asyncio
import hashlib
import importlib.metadata
import sys
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit

from .audit import EventLog
from .config import settings
from .contracts import RunRecord


ROOT = Path(__file__).resolve().parent.parent


def read_messages(path: Path) -> list[str]:
    messages = [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if not messages:
        raise ValueError("Файл обращений пуст")
    return messages


async def process(messages, gateway, log):
    from .baseline import make_draft

    records = []
    for index, message in enumerate(messages, 1):
        log.emit("message_started", message_id=index, message=message)
        record = RunRecord(message_id=index, message=message, baseline=None, checks={}, errors={})
        try:
            record.baseline = await make_draft(message, gateway)
        except Exception as exc:
            record.errors["baseline"] = type(exc).__name__
            log.emit("message_failed", message_id=index, error_type=type(exc).__name__)
        else:
            log.emit("message_completed", message_id=index, baseline=record.baseline.model_dump())
        records.append(record)
        # Save partial progress after every message, even if a later request fails.
        log.artifact("results.json", [item.model_dump(mode="json") for item in records])
    return records


async def execute(args):
    messages = read_messages(args.messages)
    config = settings(args.provider, args.env_file)
    from .model import ModelGateway

    log = EventLog(args.runs_dir, secrets=(config.api_key,))
    versions = {name: importlib.metadata.version(name) for name in ("openai-agents", "openai", "pydantic")}
    source_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in sorted((ROOT / "rehearsal").glob("*.py"))}
    log.emit("run_started", mode="baseline", provider=config.provider, model=config.model,
             provider_host=urlsplit(config.base_url).hostname if config.base_url else "api.openai.com",
             input_sha256=hashlib.sha256(args.messages.read_bytes()).hexdigest(),
             messages_count=len(messages), versions=versions, source_sha256=source_hashes, checks_enabled=False,
             semantic_spec_status="awaiting_user_definition", simulation=False)
    gateway = ModelGateway(config.model, log, api_key=config.api_key, base_url=config.base_url,
                           api_mode="chat_completions" if config.base_url else "responses",
                           structured_mode=args.structured_mode, timeout=args.timeout, retries=0)
    started = perf_counter()
    try:
        records = await process(messages, gateway, log)
    finally:
        await gateway.close()
    failures = sum(bool(record.errors) for record in records)
    log.emit("run_completed", elapsed_seconds=perf_counter() - started,
             succeeded=len(records) - failures, failed=failures)
    for record in records:
        print(f"{record.message_id}) {record.message}")
        if record.baseline:
            print(f"Категория: {record.baseline.category}")
            print(f"Черновик: {record.baseline.reply}")
        else:
            print("Ошибка: ответ не получен. Подробности в журнале запуска.")
        print()
    print(f"Результаты и журнал: {log.directory}")
    return 1 if failures else 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Пять обращений: общий агент на OpenAI Agents SDK")
    parser.add_argument("--messages", type=Path, default=ROOT / "messages.txt")
    parser.add_argument("--provider", choices=["openai", "groq", "cerebras"], default="openai")
    parser.add_argument("--env-file", type=Path, help="Файл с настройками выбранного провайдера")
    parser.add_argument("--structured-mode", choices=["native", "json_prompt"], default="json_prompt")
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--runs-dir", type=Path, default=ROOT / "runs")
    args = parser.parse_args()
    try:
        return asyncio.run(execute(args))
    except (ValueError, FileNotFoundError) as exc:
        print(f"Ошибка настройки/входа: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Запуск прерван пользователем.", file=sys.stderr)
        return 130
    except Exception as exc:
        # Provider exceptions may contain secrets; never print their body.
        print(f"Техническая ошибка: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
