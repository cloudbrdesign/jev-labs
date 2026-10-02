"""M1 checks. Run from the repo root with the venv active:

    python m01/check.py                  # replay mode (recorded real responses, no key)
    python m01/check.py --mode live      # your key; about 9 small requests
    python m01/check.py --mode offline   # scripted fake (what CI runs)

Checks look at what the code sent and how it read the answers. Probe results are printed, never
graded: the probes show behaviour, they don't test it.
"""
from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from labkit.client import make_client  # noqa: E402
from labkit.config import MODEL, SDK_PIN  # noqa: E402
from labkit.data import tickets  # noqa: E402
from labkit.transport import NotRecorded  # noqa: E402

import probes  # noqa: E402
import triage_v1  # noqa: E402

results: list[tuple[int, str]] = []


def check(n: int, name: str, ok: bool, note: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    results.append((n, status))
    print(f"{n:>2} {status}  {name}" + (f"  ({note})" if note else ""))


def run_checks(mode: str, transport=None) -> int:
    results.clear()
    print(f"M1 checks, mode={mode}\n")
    try:
        ver = md.version("typesafe-sdk")
    except md.PackageNotFoundError:
        ver = "missing"
    check(1, f"typesafe-sdk is {SDK_PIN}", ver == SDK_PIN, ver)

    spy: list = []
    inbox = {t["id"]: t for t in tickets()}
    triage_v1.DECISIONS = HERE.parent / "state" / "check_decisions.jsonl"
    if triage_v1.DECISIONS.exists():
        triage_v1.DECISIONS.unlink()
    try:
        with make_client(mode, triage_v1.REPLAY, transport=transport, spy=spy) as lab:
            check(2, "Client built in the requested mode", lab.mode == mode, lab.label("<model>"))
            responses = {tid: triage_v1.triage(lab, inbox[tid], mode) for tid in triage_v1.TICKET_IDS}
        print()
        with make_client(mode, probes.REPLAY, transport=transport, spy=[]) as lab:
            neg = probes.probe_negation(lab)
            cnt = probes.probe_counting(lab)
        print()
    except NotRecorded as e:
        check(2, "Recorded responses available for every request", False, str(e))
        return 1

    sent = [x["body"] for x in spy if x["path"] == "/v1/systemone"]
    check(3, f"Every request sent model={MODEL}", bool(sent) and all(b["model"] == MODEL for b in sent),
          f"{len(sent)} requests")
    closed = [tid for tid in triage_v1.TICKET_IDS if inbox[tid]["status"] == "closed"]
    check(4, "Closed tickets made no request", all(responses[t] is None for t in closed)
          and len(sent) == len(triage_v1.TICKET_IDS) - len(closed), ", ".join(closed))

    rs = [r for r in responses.values() if r is not None]
    check(5, "Every response answers exactly the questions asked",
          all(set(r.answers) == set(triage_v1.QUESTIONS) for r in rs))

    options = set(triage_v1.QUESTIONS["team"].criteria)
    ok6 = all(r.choices["team"].choice in options and 0 <= r.choices["team"].confidence <= 1
              and set(r.choices["team"].probabilities) == options for r in rs)
    check(6, "Choice: answer is an option, confidence in [0, 1], one probability per option", ok6)

    levels = len(triage_v1.QUESTIONS["frustration"].criteria)
    ok7 = all(0 <= r.scores["frustration"].score <= levels - 1 and len(r.scores["frustration"].legend) == levels
              and 0 <= r.scores["frustration"].confidence <= 1 for r in rs)
    check(7, "Score: value within the levels, one legend entry per level, confidence in [0, 1]", ok7)

    nouls = [r.nouls["refund_requested"] for r in rs]
    check(8, "Noul: value in [0, 1] and no confidence field",
          all(0 <= n.noul <= 1 and not hasattr(n, "confidence") for n in nouls))

    models = {r.model for r in rs}
    check(9, "Responses report a versioned model ID, not an alias",
          bool(models) and all(re.fullmatch(r"jev-\d+\.\d+\.\d+", m or "") for m in models), ", ".join(sorted(models)))

    ok10 = all((r.usage.input_tokens is None or isinstance(r.usage.input_tokens, int))
               and (r.usage.output_tokens is None or isinstance(r.usage.output_tokens, int)) for r in rs)
    check(10, "Usage tokens are integers (or reported as missing)", ok10)

    rows = [json.loads(x) for x in triage_v1.DECISIONS.read_text().splitlines()] if triage_v1.DECISIONS.exists() else []
    check(11, "Decision log has one line per call with model, request id and usage",
          len(rows) == len(rs) and all(r.get("model") and "request_id" in r and "usage" in r for r in rows), f"{len(rows)} lines")

    check(12, "Probes ran and printed their numbers",
          set(neg) == {"refund", "not_refund"} and len(cnt["nouls"]) == len(probes.ITEMS))
    check(13, "Probe B2 count is computed in code from the Noul answers",
          cnt["counted"] == sum(n > probes.YES for n in cnt["nouls"]), f"{cnt['counted']} counted, label {cnt['truth']}")

    failed = sum(s == "FAIL" for _, s in results)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("live", "replay", "offline"), default="replay")
    return run_checks(ap.parse_args().mode)


if __name__ == "__main__":
    sys.exit(main())
