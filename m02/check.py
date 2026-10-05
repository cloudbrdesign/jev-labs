"""M2 checks. Run from the repo root with the venv active:

    python m02/check.py                  # replay mode (recorded real responses, no key)
    python m02/check.py --mode live      # your key; about 16 small requests
    python m02/check.py --mode offline   # scripted fake (what CI runs)

Checks look at what the code sent and how it read the answers. Model behaviour is reported, never
graded: how many v2 routes match our labels is printed as a count, not a pass or fail.
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
from labkit.data import orders_for, ticket, tickets  # noqa: E402
from labkit.transport import NotRecorded  # noqa: E402

import experiments  # noqa: E402
import triage_v2  # noqa: E402

LABELS = json.loads((HERE / "labels.json").read_text())
PATH_RE = re.compile(r"`([A-Za-z_][\w]*(?:\.[A-Za-z_]\w*|\[\d+\])*)`")

results: list[tuple[int, str]] = []


def check(n: int, name: str, ok: bool, note: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    results.append((n, status))
    print(f"{n:>2} {status}  {name}" + (f"  ({note})" if note else ""))


def resolve(state, path: str) -> bool:
    """True if a dot-and-index path such as `ticket.body` or `order.items[0]` exists in state."""
    cur = state
    for part in re.findall(r"[A-Za-z_]\w*|\[\d+\]", path):
        if part.startswith("["):
            i = int(part[1:-1])
            if not isinstance(cur, list) or i >= len(cur):
                return False
            cur = cur[i]
        else:
            if not isinstance(cur, dict) or part not in cur:
                return False
            cur = cur[part]
    return True


def instruction_paths(instructions) -> list[str]:
    """Backticked paths in a question's text (a string, or the `question` field of an object)."""
    if isinstance(instructions, dict):
        own = set(instructions)  # names of fields inside the instruction object itself
        text = str(instructions.get("question", ""))
        return [p for p in PATH_RE.findall(text) if p.split(".")[0].split("[")[0] not in own]
    return PATH_RE.findall(str(instructions or ""))


def run_checks(mode: str, transport=None) -> int:
    results.clear()
    print(f"M2 checks, mode={mode}\n")
    try:
        ver = md.version("typesafe-sdk")
    except md.PackageNotFoundError:
        ver = "missing"
    check(1, f"typesafe-sdk is {SDK_PIN}", ver == SDK_PIN, ver)

    spy_t: list = []
    spy_e: list = []
    inbox = {t["id"]: t for t in tickets()}
    triage_v2.DECISIONS = HERE.parent / "state" / "check_decisions_v2.jsonl"
    if triage_v2.DECISIONS.exists():
        triage_v2.DECISIONS.unlink()
    try:
        with make_client(mode, triage_v2.REPLAY, transport=transport, spy=spy_t) as lab:
            check(2, "Client built in the requested mode", lab.mode == mode, lab.label("<model>"))
            out = {tid: triage_v2.triage(lab, inbox[tid], mode) for tid in triage_v2.TICKET_IDS}
        print()
        with make_client(mode, experiments.REPLAY, transport=transport, spy=spy_e) as lab:
            exp = experiments.run_all(lab)
    except NotRecorded as e:
        check(2, "Recorded responses available for every request", False, str(e))
        return 1

    responses = {tid: r for tid, (r, _) in out.items()}
    states = {tid: s for tid, (_, s) in out.items()}
    sent = [x["body"] for x in spy_t + spy_e if x["path"] == "/v1/systemone"]
    check(3, f"Every request sent model={MODEL}", bool(sent) and all(b["model"] == MODEL for b in sent),
          f"{len(sent)} requests")

    closed = [tid for tid in triage_v2.TICKET_IDS if inbox[tid]["status"] == "closed"]
    triage_sent = [x for x in spy_t if x["path"] == "/v1/systemone"]
    check(4, "Closed tickets made no request; one request per open ticket",
          all(responses[t] is None for t in closed) and len(triage_sent) == len(triage_v2.TICKET_IDS) - len(closed),
          f"{len(triage_sent)} requests, closed: {', '.join(closed)}")

    rs = {tid: r for tid, r in responses.items() if r is not None}
    check(5, "Every response answers exactly the questions asked",
          all(set(r.answers) == set(triage_v2.QUESTIONS) for r in rs.values()))

    choice_ids = [k for k, q in triage_v2.QUESTIONS.items() if q.type == "choice"]
    ok6 = "other" in triage_v2.TEAM.criteria and all(
        r.choices[q].choice in triage_v2.QUESTIONS[q].criteria
        and set(r.choices[q].probabilities) == set(triage_v2.QUESTIONS[q].criteria)
        and 0 <= r.choices[q].confidence <= 1 for r in rs.values() for q in choice_ids)
    check(6, "Choice: answer is an option, one probability per option, confidence in [0, 1]; team has `other`", ok6)

    score_ids = [k for k, q in triage_v2.QUESTIONS.items() if q.type == "score"]
    ok7 = all(0 <= r.scores[q].score <= len(triage_v2.QUESTIONS[q].criteria) - 1
              and len(r.scores[q].legend) == len(triage_v2.QUESTIONS[q].criteria)
              and 0 <= r.scores[q].confidence <= 1 for r in rs.values() for q in score_ids)
    check(7, "Score: value within its levels, one legend entry per level, confidence in [0, 1]", ok7)

    noul_ids = [k for k, q in triage_v2.QUESTIONS.items() if q.type == "noul"]
    check(8, "Noul: value in [0, 1] and no confidence field",
          all(0 <= r.nouls[q].noul <= 1 and not hasattr(r.nouls[q], "confidence") for r in rs.values() for q in noul_ids))

    models = {r.model for r in rs.values()}
    check(9, "Responses report a versioned model ID, not an alias",
          bool(models) and all(re.fullmatch(r"jev-\d+\.\d+\.\d+", m or "") for m in models), ", ".join(sorted(models)))

    routes = {tid: triage_v2.route(r.answers) for tid, r in rs.items()}
    check(10, "Speculative answers are read only on their path (order_issue for orders, detail for technical)",
          all(("order_issue" in d) == (d["team"] == "orders") and ("detail" in d) == (d["team"] == "technical")
              for d in routes.values()))

    def recompute(r):
        total = 0.0
        for q, w in triage_v2.WEIGHTS.items():
            total += w * r.scores[q].score / (len(triage_v2.QUESTIONS[q].criteria) - 1)
        return total
    pr = {tid: triage_v2.priority(r.answers) for tid, r in rs.items()}
    check(11, "Priority is computed in code from normalised Scores and lies in [0, 1]",
          all(abs(pr[t] - recompute(rs[t])) < 1e-9 and 0 <= pr[t] <= 1 for t in rs)
          and abs(sum(triage_v2.WEIGHTS.values()) - 1) < 1e-9)

    bad = []
    for x in triage_sent:
        body = x["body"]
        for qid, q in body["questions"].items():
            for p in instruction_paths(q.get("instructions")):
                if not resolve(body["state"], p):
                    bad.append(f"{qid}:{p}")
    check(12, "Every backticked path in an instruction exists in the state sent", not bad, ", ".join(bad) or "all found")

    d_out = exp.get("D", {})
    want = {o["id"] for o in orders_for(ticket(experiments.D_TICKET)["customer"])}
    check(13, "Experiment D asked one Noul per candidate order, keyed by order ID", set(d_out) == want,
          ", ".join(sorted(d_out)))

    log = [json.loads(x) for x in triage_v2.DECISIONS.read_text().splitlines()] if triage_v2.DECISIONS.exists() else []
    check(14, "Decision log has one line per call with model, request id, decision and usage",
          len(log) == len(rs) and all(r.get("model") and "request_id" in r and "decision" in r and "usage" in r for r in log),
          f"{len(log)} lines")

    check(15, "Experiments A-E ran and printed their numbers", set(exp) == set("ABCDE") and all(exp.values()))

    # Reported, not graded: model behaviour against our labels.
    match = [t for t, d in routes.items() if LABELS["team"].get(t) == d["team"]]
    print(f"\nReported (not a check): v2 team matches our labels on {len(match)} of {len(routes)} open tickets")
    for t, d in routes.items():
        flag = "ok " if t in match else "-- "
        print(f"   {flag}{t}  v2={d['team']:<9} label={LABELS['team'].get(t)}")

    failed = sum(s == "FAIL" for _, s in results)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("live", "replay", "offline"), default="replay")
    return run_checks(ap.parse_args().mode)


if __name__ == "__main__":
    sys.exit(main())
