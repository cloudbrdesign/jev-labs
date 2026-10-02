"""make_client(mode): the one place the labs build a TypeSafe client.

    live     your own TYPESAFE_API_KEY; real calls to Jev (add record_to=... to save them)
    replay   real responses recorded on the course's machine; no key, no network
    offline  scripted fake answers (not Jev); used by the self-tests and CI
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import httpx2
from typesafe_sdk import TypeSafeClient, TypeSafeError

from labkit.banner import banner
from labkit.config import MODEL, PLACEHOLDER_KEY
from labkit.env import api_key
from labkit.transport import RecordingTransport, ReplayTransport, SpyTransport, fake_handler

MODES = ("live", "replay", "offline")


@dataclass
class LabClient:
    client: TypeSafeClient
    mode: str
    recorded_on: str | None = None

    def label(self, model: str | None) -> str:
        return banner(self.mode, model, self.recorded_on)

    def __enter__(self) -> "LabClient":
        self.client.__enter__()
        return self

    def __exit__(self, *exc) -> None:
        self.client.__exit__(*exc)


def make_client(mode: str, replay_file: Path, record: bool = False,
                transport: httpx2.BaseTransport | None = None, spy: list | None = None) -> LabClient:
    """Build a client for `mode`.

    `transport` lets tests inject their own fake; `spy` (a list) collects every request body.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    recorded_on = None
    if mode == "live":
        key = api_key()
        if not key:
            raise TypeSafeError("TYPESAFE_API_KEY is not set. Put it in your shell or in .env, "
                                "or run this lab with --mode replay.")
        t = transport or (RecordingTransport(replay_file) if record else None)  # None = SDK default
    elif mode == "replay":
        key = PLACEHOLDER_KEY
        t = transport or ReplayTransport(replay_file)
        recorded_on = t.recorded_on() if isinstance(t, ReplayTransport) else None
    else:
        key = PLACEHOLDER_KEY
        t = transport or httpx2.MockTransport(fake_handler)
    if spy is not None:
        t = SpyTransport(t or httpx2.HTTPTransport(), spy)
    return LabClient(TypeSafeClient(api_key=key, model=MODEL, transport=t), mode, recorded_on)


def mode_args(description: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--mode", choices=MODES, default="replay",
                    help="live (your key), replay (recorded real responses, default), offline (fake)")
    ap.add_argument("--record", action="store_true",
                    help="live mode only: also save each exchange to this lab's replay file")
    return ap


def run(main) -> int:
    """Run a lab script; turn the two expected setup errors into one clear line."""
    from labkit.transport import NotRecorded

    try:
        return main()
    except NotRecorded as e:
        print(f"Replay: {e}")
    except TypeSafeError as e:
        print(f"{type(e).__name__}: {e}")
    return 1
