"""Read TYPESAFE_API_KEY from the environment or a local .env file (never printed)."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Set variables from a simple KEY=value .env file without overriding the shell."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


def api_key() -> str | None:
    load_dotenv()
    return os.environ.get("TYPESAFE_API_KEY") or None


def key_status() -> str:
    return "set" if api_key() else "not set"
