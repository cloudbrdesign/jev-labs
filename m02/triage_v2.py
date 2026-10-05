"""M2 lab: triage v2 for the Lanternfield support inbox, with all three question types.

Fixes the two v1 misroutes (the `team` Choice now has `orders` and `other`), sends a structured
state (the ticket and the customer's latest order), and asks every question the code might need
in ONE request per ticket. Code routes on the `team` Choice only. Nouls and the priority are
printed and logged, with no thresholds: Module 3 is where thresholds are chosen.

    python m02/triage_v2.py                 # replay (recorded real responses)
    python m02/triage_v2.py --mode live     # your key
    python m02/triage_v2.py --mode offline  # scripted fake
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typesafe_sdk import Choice, Noul, NoulCriteria, Score  # noqa: E402

from labkit.client import make_client, mode_args, run  # noqa: E402
from labkit.data import order_view, orders_for, tickets  # noqa: E402
from labkit.show import request_id  # noqa: E402

HERE = Path(__file__).resolve().parent
REPLAY = HERE / "replay" / "triage.jsonl"
DECISIONS = HERE.parent / "state" / "decisions_v2.jsonl"
TICKET_IDS = ["LT-001", "LT-002", "LT-003", "LT-004", "LT-005", "LT-006", "LT-007", "LT-008"]

# --- questions -------------------------------------------------------------------------------
# Question IDs (the dict keys) are for our code; the model never sees them. Each instruction says
# in full what is asked, and points at a field of the state with a backticked path.

TEAM = Choice(
    instructions="Which team should handle the request in `ticket.body`?",
    criteria={
        "billing": {
            "what": "Charges, refunds of money already paid, invoices, payment problems",
            "not_for": "Where an order is, or sizes, swaps and returns of items",
            "examples": ["I was charged twice", "When will my refund reach my card?"],
        },
        "orders": {
            "what": "Order status, late or missing deliveries, wrong sizes, exchanges and returns",
            "not_for": "Charges or payment problems",
            "examples": ["My parcel hasn't arrived", "These boots don't fit, can I swap them?"],
        },
        "technical": "A product that doesn't work as expected, or how to use it",
        "account": "Logging in, passwords, email address, profile",
        "other": "None of the above",
    },
)

QUESTIONS = {
    "team": TEAM,
    # Speculative: only read when team is "orders". Asking it costs a few tokens, not a request.
    "order_issue": Choice(
        instructions="If `ticket.body` reports a problem with an order, which kind is it?",
        criteria={
            "wrong_size": "The item doesn't fit",
            "not_delivered": "The parcel hasn't arrived",
            "damaged": "The item arrived broken or faulty",
            "wrong_item": "A different product was delivered",
            "other": "An order problem that fits none of the above, or no problem stated",
        },
    ),
    "requested_resolution": Choice(
        instructions="What does the customer in `ticket.body` want to happen?",
        criteria={
            "refund": "Money back",
            "exchange": "Swap the item for a different one",
            "replacement": "The same item sent again, or the missing item delivered",
            "information": "An answer or instructions, no action on the order",
            "other": "Something else",
        },
    ),
    "frustration": Score(
        instructions="How frustrated is the customer who wrote `ticket.body`?",
        criteria=[
            "Calm, just stating facts",
            "Annoyed but polite",
            "Angry, demanding, or saying they have had enough",
            "Abusive or threatening toward staff",
        ],
    ),
    "urgency": Score(
        instructions="How time-pressured is the request in `ticket.body`?",
        criteria=[
            "No deadline or time pressure mentioned",
            "Wants it soon, but nothing is blocked",
            "A trip, event or task is blocked within days",
        ],
    ),
    # Speculative: only read for technical tickets.
    "detail": Score(
        instructions="How much does `ticket.body` tell an engineer about a product problem?",
        criteria=[
            "No detail; just says something is wrong",
            "Names the product but not what was done",
            "Says what was done and what happened",
        ],
    ),
    "wants_human": Noul(instructions="Does the customer in `ticket.body` ask to talk to a person?"),
    "repeat_contact": Noul(
        instructions="Has the customer contacted support about this before?",
        criteria=NoulCriteria(
            true="Mentions an earlier email, call, ticket, or that they have asked before",
            false="No sign of any earlier contact",
        ),
    ),
    # Same wording as v1, so its value can be compared with Module 1's run.
    "refund_requested": Noul(instructions="Does the customer ask for money back or for a charge to be reversed?"),
}

QUEUES = {"billing": "Billing desk", "orders": "Orders desk", "technical": "Product support",
          "account": "Account team", "other": "Front desk"}

# Priority from normalised Scores. The weights are ours: change them when the ranking doesn't match
# what the support lead would do. Logged only in M2.
WEIGHTS = {"urgency": 0.6, "frustration": 0.4}


def build_state(ticket: dict) -> dict:
    """Ticket text plus the customer's latest order (a code rule; Module 2 experiment D shows
    asking the model which order a ticket is about when a customer has several)."""
    recent = orders_for(ticket["customer"])
    return {
        "ticket": {"subject": ticket["subject"], "body": ticket["body"]},
        "order": order_view(recent[0]) if recent else None,
    }


def normalised(answer, question: Score) -> float:
    """A Score on 0..1: divide by the top level number, len(criteria) - 1."""
    return answer.score / (len(question.criteria) - 1)


def priority(answers) -> float:
    return sum(w * normalised(answers[q], QUESTIONS[q]) for q, w in WEIGHTS.items())


def log_decision(row: dict) -> None:
    DECISIONS.parent.mkdir(exist_ok=True)
    with DECISIONS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def route(answers) -> dict:
    """Plain `if` statements on typed answers. Only the Choice decides the queue."""
    team = answers["team"].choice
    decision = {"team": team, "queue": QUEUES[team]}
    if team == "orders":
        decision["order_issue"] = answers["order_issue"].choice  # speculative answer used here only
    if team == "technical":
        decision["detail"] = round(answers["detail"].score, 2)
    return decision


def triage(lab, ticket: dict, mode: str):
    if ticket["status"] == "closed":
        print(f"{ticket['id']}  closed -> no model call (decided in code)")
        return None, None
    state = build_state(ticket)
    r = lab.client.system_one(state, QUESTIONS)
    a = r.answers
    d = route(a)
    d["priority"] = round(priority(a), 2)
    team = a["team"]
    split = " ".join(f"{k}={v:.2f}" for k, v in sorted(team.probabilities.items(), key=lambda kv: -kv[1]) if v >= 0.01)
    extra = f" issue={d['order_issue']}" if "order_issue" in d else ""
    print(f"{ticket['id']}  {d['queue']:<15} team={team.choice}{extra}  [{split}]")
    print(f"        resolution={a['requested_resolution'].choice} frustration={a['frustration'].score:.2f} "
          f"urgency={a['urgency'].score:.2f} priority={d['priority']:.2f} | wants_human={a['wants_human'].noul:.2f} "
          f"repeat_contact={a['repeat_contact'].noul:.2f} refund_requested={a['refund_requested'].noul:.2f}")
    log_decision({"ticket": ticket["id"], "mode": mode, "model": r.model, "request_id": request_id(r),
                  "decision": d, "answers": {k: v.model_dump() for k, v in a.items()},
                  "usage": r.usage.model_dump()})
    return r, state


def main() -> int:
    args = mode_args(__doc__).parse_args()
    if args.record and args.mode != "live":
        print("--record only works with --mode live")
        return 2
    inbox = {t["id"]: t for t in tickets()}
    with make_client(args.mode, REPLAY, record=args.record) as lab:
        first = None
        for tid in TICKET_IDS:
            r, _ = triage(lab, inbox[tid], args.mode)
            if r is not None and first is None:
                first = r
                print("   " + lab.label(r.model))
    print(f"Decisions appended to {DECISIONS.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(run(main))
