"""HTTP transports for the three lab modes.

The TypeSafe Python SDK accepts a custom `transport` (an httpx2 transport). The labs use it to:

- record a live run (RecordingTransport wraps the real network transport and writes each
  request/response pair to a JSON-lines file, without any headers, so no key is ever stored);
- replay a recorded run (ReplayTransport answers from that file, matched by the request);
- run offline with scripted answers (fake_handler + httpx2.MockTransport), for CI.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import httpx2

REQUEST_ID_HEADER = "x-typesafe-request-id"


def request_key(method: str, path: str, body: bytes) -> str:
    """A stable key for a request: method, path and the JSON body with sorted keys."""
    text = ""
    if body:
        try:
            text = json.dumps(json.loads(body), sort_keys=True, separators=(",", ":"))
        except ValueError:
            text = body.decode("utf-8", "replace")
    return hashlib.sha256(f"{method} {path} {text}".encode()).hexdigest()


def _sdk_version() -> str:
    import typesafe_sdk

    return getattr(typesafe_sdk, "__version__", "unknown")


class RecordingTransport(httpx2.BaseTransport):
    """Send requests for real and append each exchange to a JSON-lines replay file."""

    def __init__(self, path: Path, inner: httpx2.BaseTransport | None = None) -> None:
        self.path = Path(path)
        self.inner = inner or httpx2.HTTPTransport()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        body = request.read()
        response = self.inner.handle_request(request)
        content = response.read()
        try:
            response_json = json.loads(content) if content else None
        except ValueError:
            response_json = None
        entry = {
            "key": request_key(request.method, request.url.path, body),
            "method": request.method,
            "path": request.url.path,
            "request": json.loads(body) if body else None,
            "status": response.status_code,
            "response": response_json,
            "request_id": response.headers.get(REQUEST_ID_HEADER),
            "model": (response_json or {}).get("model") if isinstance(response_json, dict) else None,
            "sdk_version": _sdk_version(),
            "recorded_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return httpx2.Response(response.status_code, content=content,
                               headers={"content-type": "application/json",
                                        **({REQUEST_ID_HEADER: entry["request_id"]} if entry["request_id"] else {})})

    def close(self) -> None:
        self.inner.close()


class SpyTransport(httpx2.BaseTransport):
    """Pass requests through to `inner` and keep a copy of each request body (for checks)."""

    def __init__(self, inner: httpx2.BaseTransport, log: list) -> None:
        self.inner, self.log = inner, log

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        body = request.read()
        self.log.append({"method": request.method, "path": request.url.path,
                         "body": json.loads(body) if body else None})
        return self.inner.handle_request(request)

    def close(self) -> None:
        self.inner.close()


class NotRecorded(LookupError):
    """Raised when replay mode is asked for a request that was never recorded."""


def load_replay(path: Path) -> dict[str, dict]:
    entries: dict[str, dict] = {}
    p = Path(path)
    if not p.exists():
        return entries
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            entries[e["key"]] = e  # the latest recording of the same request wins
    return entries


class ReplayTransport(httpx2.BaseTransport):
    """Answer from a replay file. A request that wasn't recorded raises NotRecorded."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.entries = load_replay(self.path)

    def recorded_on(self) -> str | None:
        dates = sorted({e.get("recorded_utc", "")[:10] for e in self.entries.values()} - {""})
        return dates[-1] if dates else None

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        body = request.read()
        key = request_key(request.method, request.url.path, body)
        entry = self.entries.get(key)
        if entry is None:
            raise NotRecorded(
                f"This request was not recorded in {self.path.name}. Run it in live mode with "
                "your own key, or use the questions and tickets exactly as the lab ships them.")
        headers = {"content-type": "application/json"}
        if entry.get("request_id"):
            headers[REQUEST_ID_HEADER] = entry["request_id"]
        return httpx2.Response(entry["status"], json=entry["response"], headers=headers)


# ----------------------------------------------------------------------------- offline fake

def _fraction(*parts: str) -> float:
    """A deterministic number in [0, 1) from text, so the fake gives varied but stable answers."""
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def fake_answer(qid: str, question: dict, state_text: str) -> dict:
    kind = question.get("type")
    if kind == "noul":
        return {"type": "noul", "noul": round(_fraction(qid, state_text), 2)}
    if kind == "choice":
        options = list(question.get("criteria") or {})
        top = int(_fraction(qid, state_text) * len(options)) % len(options)
        rest = (0.3 / (len(options) - 1)) if len(options) > 1 else 0.0
        probs = {o: (0.7 if i == top else rest) for i, o in enumerate(options)}
        return {"type": "choice", "choice": options[top], "probabilities": probs, "confidence": 0.5}
    if kind == "score":
        levels = list(question.get("criteria") or [])
        n = len(levels)
        top = int(_fraction(qid, state_text) * n) % n
        probs = {str(i): (0.8 if i == top else 0.2 / (n - 1)) for i in range(n)}
        score = sum(i * p for i, p in zip(range(n), probs.values()))
        legend = {str(i): (lv if isinstance(lv, str) else json.dumps(lv)) for i, lv in enumerate(levels)}
        return {"type": "score", "score": round(score, 2), "legend": legend,
                "probabilities": probs, "confidence": 0.5}
    raise ValueError(f"unknown question type {kind!r}")


FAKE_MODELS = {"models": [
    {"name": "jev-latest", "description": "offline fake entry", "release_date": "2026-01-01"},
    {"name": "jev-preview", "description": "offline fake entry", "release_date": "2026-01-01"},
]}


def fake_handler(request: httpx2.Request) -> httpx2.Response:
    """Scripted stand-in for the API. Shape follows the documented response body."""
    if request.method == "GET" and request.url.path == "/v1/models":
        return httpx2.Response(200, json=FAKE_MODELS)
    payload = json.loads(request.read())
    state_text = json.dumps(payload.get("state"), sort_keys=True)
    answers = {qid: fake_answer(qid, q, state_text) for qid, q in payload["questions"].items()}
    return httpx2.Response(
        200,
        json={"model": payload.get("model"), "answers": answers,
              "usage": {"input_tokens": 100 + 10 * len(answers), "output_tokens": 5 * len(answers)}},
        headers={REQUEST_ID_HEADER: "offline-" + request_key("POST", "/v1/systemone", request.content)[:12]},
    )
