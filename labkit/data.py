"""The Lanternfield Outdoor Supply support inbox (fictional company, our own text)."""
from __future__ import annotations

import json
from pathlib import Path

INBOX = Path(__file__).resolve().parent.parent / "data" / "inbox.jsonl"


def tickets() -> list[dict]:
    return [json.loads(line) for line in INBOX.read_text(encoding="utf-8").splitlines() if line.strip()]


def ticket(ticket_id: str) -> dict:
    for t in tickets():
        if t["id"] == ticket_id:
            return t
    raise KeyError(ticket_id)


def as_state(t: dict) -> dict:
    """The part of a ticket the model sees: subject and body only."""
    return {"subject": t["subject"], "body": t["body"]}
