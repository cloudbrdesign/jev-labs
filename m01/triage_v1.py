"""M1 lab: first typed decisions for the Lanternfield support inbox.

Code decides what it can (closed tickets never reach the model). For each open ticket, one
request asks three typed questions; code picks the queue from the Choice answer.

    python m01/triage_v1.py                 # replay (recorded real responses)
    python m01/triage_v1.py --mode live     # your key
    python m01/triage_v1.py --mode offline  # scripted fake
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typesafe_sdk import Choice, Noul, Score  # noqa: E402

from labkit.client import make_client, mode_args, run  # noqa: E402
from labkit.data import as_state, tickets  # noqa: E402
from labkit.show import request_id  # noqa: E402

HERE = Path(__file__).resolve().parent
REPLAY = HERE / "replay" / "triage.jsonl"
DECISIONS = HERE.parent / "state" / "decisions.jsonl"
TICKET_IDS = ["LT-001", "LT-002", "LT-003", "LT-004", "LT-005", "LT-006"]

QUESTIONS = {
    "team": Choice(
        instructions="Which team should handle this support message?",
        criteria={
            "billing": "Payments, charges, refunds, invoices",
            "technical": "A product that doesn't work as expected",
            "account": "Logging in, passwords, profile and order access",
        },
    ),
    "frustration": Score(
        instructions="How frustrated is the customer?",
        criteria=["Calm and patient", "Annoyed", "Angry and demanding urgent action"],
    ),
    "refund_requested": Noul(instructions="Does the customer ask for money back or for a charge to be reversed?"),
}
QUEUES = {"billing": "Billing desk", "technical": "Product support", "account": "Account team"}


def log_decision(row: dict) -> None:
    DECISIONS.parent.mkdir(exist_ok=True)
    with DECISIONS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def triage(lab, ticket: dict, mode: str):
    if ticket["status"] == "closed":
        print(f"{ticket['id']}  closed -> no model call (decided in code)")
        return None
    r = lab.client.system_one(as_state(ticket), QUESTIONS)
    team = r.choices["team"]
    print(f"{ticket['id']}  {QUEUES[team.choice]:<16} team={team.choice} "
          f"frustration={r.scores['frustration'].score:.2f} refund_requested={r.nouls['refund_requested'].noul:.2f}")
    log_decision({"ticket": ticket["id"], "mode": mode, "model": r.model, "request_id": request_id(r),
                  "answers": {k: v.model_dump() for k, v in r.answers.items()},
                  "usage": r.usage.model_dump()})
    return r


def main() -> int:
    args = mode_args(__doc__).parse_args()
    if args.record and args.mode != "live":
        print("--record only works with --mode live")
        return 2
    inbox = {t["id"]: t for t in tickets()}
    with make_client(args.mode, REPLAY, record=args.record) as lab:
        first = None
        for tid in TICKET_IDS:
            r = triage(lab, inbox[tid], args.mode)
            if r is not None and first is None:
                first = r
                print("   " + lab.label(r.model))
    print(f"Decisions appended to {DECISIONS.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(run(main))
