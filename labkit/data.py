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


# ----------------------------------------------------------------------------- orders (M2)

ORDERS = INBOX.parent / "orders.jsonl"


def orders() -> list[dict]:
    return [json.loads(line) for line in ORDERS.read_text(encoding="utf-8").splitlines() if line.strip()]


def orders_for(customer: str) -> list[dict]:
    """A customer's orders, newest first (ISO dates sort as text; date logic stays in code)."""
    return sorted((o for o in orders() if o["customer"] == customer), key=lambda o: o["placed"], reverse=True)


def order_view(o: dict) -> dict:
    """The part of an order record the model sees: no customer ID, no internal dates to compare."""
    return {"id": o["id"], "status": o["status"], "carrier_status": o["carrier_status"],
            "items": o["items"], "payments": o["payments"]}
