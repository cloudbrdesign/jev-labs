"""M1 offline self-test: the real SDK with scripted answers runs all 13 checks. No key, no network."""
from __future__ import annotations

import sys
from pathlib import Path

import httpx2

M01 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(M01.parent))
sys.path.insert(0, str(M01))

import check  # noqa: E402
from labkit.transport import fake_handler  # noqa: E402


def test_all_checks_pass_offline():
    assert check.run_checks("offline") == 0


def test_alias_in_response_fails_check_9():
    def handler(req):
        r = fake_handler(req)
        if req.url.path == "/v1/systemone":
            body = r.json()
            body["model"] = "jev-latest"
            return httpx2.Response(200, json=body, headers=dict(r.headers))
        return r
    assert check.run_checks("offline", transport=httpx2.MockTransport(handler)) == 1
    assert (9, "FAIL") in check.results


def test_missing_replay_fails_cleanly(tmp_path, monkeypatch):
    import probes
    import triage_v1
    monkeypatch.setattr(triage_v1, "REPLAY", tmp_path / "none.jsonl")
    monkeypatch.setattr(probes, "REPLAY", tmp_path / "none2.jsonl")
    assert check.run_checks("replay") == 1


def test_missing_request_id_header_is_reported_not_crashing():
    def handler(req):
        r = fake_handler(req)
        return httpx2.Response(r.status_code, json=r.json())  # no request-id header
    assert check.run_checks("offline", transport=httpx2.MockTransport(handler)) == 0
