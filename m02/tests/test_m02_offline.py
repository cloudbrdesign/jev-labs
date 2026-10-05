"""M2 offline self-test: the real SDK with scripted answers runs all 15 checks. No key, no network."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import httpx2
from typesafe_sdk import Choice

M02 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(M02.parent))
sys.path.insert(0, str(M02))

from labkit.transport import fake_handler  # noqa: E402


def _load(name: str, file: str):
    """Load m02's own module under a unique name (m00/m01 also have a `check.py`)."""
    spec = importlib.util.spec_from_file_location(name, M02 / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


check = _load("m02_check", "check.py")
triage_v2 = check.triage_v2
experiments = check.experiments


def test_all_checks_pass_offline():
    assert check.run_checks("offline") == 0


def test_alias_in_response_fails_check_9():
    def handler(req):
        r = fake_handler(req)
        body = r.json()
        body["model"] = "jev-latest"
        return httpx2.Response(200, json=body, headers=dict(r.headers))
    assert check.run_checks("offline", transport=httpx2.MockTransport(handler)) == 1
    assert (9, "FAIL") in check.results


def test_path_missing_from_state_fails_check_12(monkeypatch):
    bad = Choice(instructions="Which team should handle `ticket.message`?", criteria=dict(triage_v2.TEAM.criteria))
    monkeypatch.setitem(triage_v2.QUESTIONS, "team", bad)
    assert check.run_checks("offline") == 1
    assert (12, "FAIL") in check.results


def test_resolve_paths():
    state = {"ticket": {"body": "x"}, "order": {"items": ["a", "b"]}}
    assert check.resolve(state, "ticket.body")
    assert check.resolve(state, "order.items[1]")
    assert not check.resolve(state, "order.items[2]")
    assert not check.resolve(state, "ticket.subject")
    assert check.instruction_paths({"candidate_order": {}, "question": "Is `ticket.body` about `candidate_order`?"}) == ["ticket.body"]


def test_missing_replay_fails_cleanly(tmp_path, monkeypatch):
    monkeypatch.setattr(triage_v2, "REPLAY", tmp_path / "none.jsonl")
    monkeypatch.setattr(experiments, "REPLAY", tmp_path / "none2.jsonl")
    assert check.run_checks("replay") == 1


def test_missing_request_id_header_is_reported_not_crashing():
    def handler(req):
        r = fake_handler(req)
        return httpx2.Response(r.status_code, json=r.json())
    assert check.run_checks("offline", transport=httpx2.MockTransport(handler)) == 0
