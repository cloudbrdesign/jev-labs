"""One line that says where an answer came from. Printed before every result."""
from __future__ import annotations


def banner(mode: str, model: str | None, recorded_on: str | None = None) -> str:
    if mode == "live":
        return f"[LIVE] model={model}"
    if mode == "replay":
        return f"[RECORDED {recorded_on or 'date unknown'}] model={model} (replayed, not a live call)"
    return f"[OFFLINE FAKE] model={model} (scripted answers, not Jev)"
