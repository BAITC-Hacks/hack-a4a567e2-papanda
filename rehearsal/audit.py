"""Local event log. Credentials and hidden reasoning are never intentional inputs."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class EventLog:
    def __init__(self, root: Path, secrets: tuple[str, ...] = ()):
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
        self.directory = root / self.run_id
        self.directory.mkdir(parents=True, exist_ok=False)
        self.secrets = tuple(value for value in secrets if value)
        self.sequence = 0

    def clean(self, value):
        if isinstance(value, dict):
            return {
                key: "[REDACTED]" if re.search(
                    r"api.?key|authorization|password|credential|secret|access.?token|refresh.?token",
                    str(key), re.I,
                ) else self.clean(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [self.clean(item) for item in value]
        if isinstance(value, str):
            for secret in self.secrets:
                value = value.replace(secret, "[REDACTED]")
            value = re.sub(r"\bsk-[A-Za-z0-9_-]+", "[REDACTED]", value)
            value = re.sub(r"\bBearer\s+\S+", "Bearer [REDACTED]", value, flags=re.I)
        return value

    def emit(self, event: str, **data):
        self.sequence += 1
        row = {
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "sequence": self.sequence,
            "event": event,
            "data": self.clean(data),
        }
        with (self.directory / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    def artifact(self, name: str, value):
        if Path(name).name != name:
            raise ValueError("Artifact name must be a filename")
        (self.directory / name).write_text(
            json.dumps(self.clean(value), ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
