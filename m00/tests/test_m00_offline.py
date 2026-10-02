"""M0 offline self-test: the real TypeSafe SDK against scripted fakes. No key, no network."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx2
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from typesafe_sdk import Noul, TypeSafeAuthenticationError, TypeSafeClient, TypeSafeError  # noqa: E402

from labkit.client import make_client  # noqa: E402
from labkit.config import MODEL, PLACEHOLDER_KEY  # noqa: E402
from labkit.transport import NotRecorded, RecordingTransport, ReplayTransport, fake_handler  # noqa: E402

Q = {"refund_requested": Noul(instructions="Does this message ask for a refund?")}
STATE = {"subject": "Charged twice", "body": "Please reverse the extra charge."}


def test_request_shape_and_answer():
    seen = []

    def handler(req):
        seen.append(req)
        return fake_handler(req)

    with make_client("offline", Path("unused"), transport=httpx2.MockTransport(handler)) as lab:
        r = lab.client.system_one(STATE, Q)
    body = json.loads(seen[0].content)
    assert seen[0].method == "POST" and seen[0].url.path == "/v1/systemone"
    assert body["model"] == MODEL
    assert body["questions"]["refund_requested"]["type"] == "noul"
    assert 0 <= r.nouls["refund_requested"].noul <= 1
    assert isinstance(r.usage.input_tokens, int)


def test_usage_none_is_handled():
    def handler(req):
        return httpx2.Response(200, json={"model": MODEL, "answers": {"refund_requested": {"type": "noul", "noul": 0.5}},
                                          "usage": {}})
    from labkit.show import tokens
    with make_client("offline", Path("unused"), transport=httpx2.MockTransport(handler)) as lab:
        r = lab.client.system_one(STATE, Q)
    assert "not reported" in tokens(r.usage)


def test_missing_key_fails_before_any_request(monkeypatch, tmp_path):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr("labkit.env.load_dotenv", lambda *a, **k: None)
    with pytest.raises(TypeSafeError):
        make_client("live", tmp_path / "x.jsonl")


def test_401_raises_authentication_error():
    def handler(req):
        return httpx2.Response(401, json={"error": {"message": "invalid key"}})
    client = TypeSafeClient(api_key=PLACEHOLDER_KEY, model=MODEL, transport=httpx2.MockTransport(handler))
    with client, pytest.raises(TypeSafeAuthenticationError):
        client.system_one(STATE, Q)


def test_record_then_replay_round_trip(tmp_path):
    replay = tmp_path / "rec.jsonl"
    rec = RecordingTransport(replay, inner=httpx2.MockTransport(fake_handler))
    with TypeSafeClient(api_key="secret-value-123", model=MODEL, transport=rec) as c:
        c.models.list()
        live = c.system_one(STATE, Q)
    text = replay.read_text()
    assert "secret-value-123" not in text and "authorization" not in text.lower()
    lines = [json.loads(x) for x in text.splitlines()]
    assert {x["path"] for x in lines} == {"/v1/models", "/v1/systemone"}
    assert all(x["sdk_version"] and x["recorded_utc"] for x in lines)
    with make_client("replay", replay) as lab:
        again = lab.client.system_one(STATE, Q)
        assert lab.recorded_on is not None
    assert again.nouls["refund_requested"].noul == live.nouls["refund_requested"].noul
    assert again.request_id == live.request_id


def test_replay_miss_raises(tmp_path):
    replay = tmp_path / "empty.jsonl"
    replay.write_text("")
    with make_client("replay", replay) as lab, pytest.raises(NotRecorded):
        lab.client.system_one(STATE, {"other": Noul(instructions="Is this about boots?")})


def test_replay_transport_reports_date(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text(json.dumps({"key": "k", "recorded_utc": "2026-10-03 09:00 UTC"}) + "\n")
    assert ReplayTransport(p).recorded_on() == "2026-10-03"
