"""M2 experiments: five small runs behind the lessons. Each is an experiment, not a test: it
prints what the model returned, and we never stage a result.

    A  (2.4) Score levels as bare numbers vs levels that describe situations
    B  (2.1) a Noul "very frustrated?" next to a frustration Score: a Noul is not a degree
    C  (2.3) Module 1's team options vs Module 2's (with `orders` and `other`)
    D  (2.5) which of a customer's orders is a ticket about? one Noul per order, built in code
    E  (2.2) one Noul with two conditions vs two Nouls, one condition each

    python m02/experiments.py [--only A,C] [--mode live|replay|offline] [--record]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from typesafe_sdk import Choice, Noul, Score  # noqa: E402

from labkit.client import make_client, mode_args, run  # noqa: E402
from labkit.data import as_state, order_view, orders_for, ticket  # noqa: E402
from labkit.config import MODEL  # noqa: E402
from labkit.show import response_footer  # noqa: E402

import triage_v2  # noqa: E402

HERE = Path(__file__).resolve().parent
REPLAY = HERE / "replay" / "experiments.jsonl"
TAG = "(experiment, not a test)"


def dist(probabilities: dict) -> str:
    return " ".join(f"{k}={v:.2f}" for k, v in probabilities.items())


# --- A: numbers-only levels vs situation levels ------------------------------------------------
A_TICKET = "LT-002"
A_QUESTIONS = {
    "severity_numbers": Score(
        instructions="Rate how serious the problem in `body` is from 0 to 2, where 2 is worst.",
        criteria=["0", "1", "2"],
    ),
    "severity_situations": Score(
        instructions="How serious is the problem in `body`?",
        criteria=[
            "A question about use; the product works",
            "The product partly works, or there is a workaround",
            "The product can't be used at all",
        ],
    ),
}


def experiment_a(lab) -> dict:
    print(f"A  Score levels: numbers only vs situations, {A_TICKET}  {TAG}")
    r = lab.client.system_one(as_state(ticket(A_TICKET)), A_QUESTIONS)
    out = {}
    for qid in A_QUESTIONS:
        s = r.scores[qid]
        out[qid] = s
        print(f"   {qid:<20} score={s.score:.2f} confidence={s.confidence:.2f}  {dist(s.probabilities)}")
    print(f"   {response_footer(r)}")
    return out


# --- B: a Noul is not a degree -----------------------------------------------------------------
B_TICKETS = ["LT-001", "LT-003", "LT-006"]
B_QUESTIONS = {
    "very_frustrated": Noul(instructions="Is the customer who wrote `body` very frustrated?"),
    "frustration": Score(
        instructions="How frustrated is the customer who wrote `body`?",
        criteria=triage_v2.QUESTIONS["frustration"].criteria,
    ),
}


def experiment_b(lab) -> dict:
    print(f"B  Noul 'very frustrated?' vs a 4-level frustration Score  {TAG}")
    out = {}
    for tid in B_TICKETS:
        r = lab.client.system_one(as_state(ticket(tid)), B_QUESTIONS)
        n, s = r.nouls["very_frustrated"].noul, r.scores["frustration"]
        out[tid] = (n, s)
        print(f"   {tid}  noul={n:.2f}   score={s.score:.2f} (0-3) confidence={s.confidence:.2f}")
    print(f"   last request: {response_footer(r)}")
    return out


# --- C: Module 1's options vs Module 2's ------------------------------------------------------
C_TICKETS = ["LT-005", "LT-006"]
C_QUESTIONS = {
    "team_v1": Choice(  # exactly Module 1's question
        instructions="Which team should handle this support message?",
        criteria={
            "billing": "Payments, charges, refunds, invoices",
            "technical": "A product that doesn't work as expected",
            "account": "Logging in, passwords, profile and order access",
        },
    ),
    "team_v2": triage_v2.TEAM,
}


def experiment_c(lab) -> dict:
    print(f"C  team options: Module 1 vs Module 2 (one request per ticket, answers independent)  {TAG}")
    out = {}
    for tid in C_TICKETS:
        t = ticket(tid)
        state = {"ticket": as_state(t)}  # same ticket text for both questions
        r = lab.client.system_one(state, C_QUESTIONS)
        v1, v2 = r.choices["team_v1"], r.choices["team_v2"]
        out[tid] = (v1, v2)
        print(f"   {tid}  v1: {v1.choice:<9} conf={v1.confidence:.2f}  [{dist(v1.probabilities)}]")
        print(f"          v2: {v2.choice:<9} conf={v2.confidence:.2f}  [{dist(v2.probabilities)}]")
    print(f"   last request: {response_footer(r)}")
    return out


# --- D: one Noul per candidate order, built in code -----------------------------------------
D_TICKET = "LT-006"
D_QUESTION = "Is the message in `ticket.body` about `candidate_order`?"


def d_questions(candidates: list[dict]) -> dict[str, Noul]:
    """Same question for every order; the record goes in its own field, keys carry the order ID."""
    return {f"about_{o['id']}": Noul(instructions={"candidate_order": order_view(o), "question": D_QUESTION})
            for o in candidates}


def experiment_d(lab) -> dict:
    t = ticket(D_TICKET)
    candidates = orders_for(t["customer"])
    print(f"D  which order is {D_TICKET} about? {len(candidates)} orders, one Noul each, one request  {TAG}")
    r = lab.client.system_one({"ticket": as_state(t)}, d_questions(candidates))
    out = {}
    for qid, a in sorted(r.nouls.items(), key=lambda kv: -kv[1].noul):
        oid = qid.removeprefix("about_")
        out[oid] = a.noul
        o = next(c for c in candidates if c["id"] == oid)
        print(f"   {oid}  noul={a.noul:.2f}  {', '.join(o['items'])} ({o['status']})")
    print(f"   {response_footer(r)}")
    return out


# --- E: one condition per Noul ---------------------------------------------------------------
E_TICKETS = ["LT-001", "LT-006"]
E_QUESTIONS = {
    "angry_and_refund": Noul(instructions="Is the customer who wrote `body` angry and asking for a refund?"),
    "angry": Noul(instructions="Is the customer who wrote `body` angry?"),
    "refund": Noul(instructions="Does the customer who wrote `body` ask for money back?"),
}


def experiment_e(lab) -> dict:
    print(f"E  one Noul with two conditions vs two Nouls  {TAG}")
    out = {}
    for tid in E_TICKETS:
        r = lab.client.system_one(as_state(ticket(tid)), E_QUESTIONS)
        v = {k: r.nouls[k].noul for k in E_QUESTIONS}
        out[tid] = v
        print(f"   {tid}  angry_and_refund={v['angry_and_refund']:.2f}   angry={v['angry']:.2f}  refund={v['refund']:.2f}")
    print(f"   last request: {response_footer(r)}")
    return out


EXPERIMENTS = {"A": experiment_a, "B": experiment_b, "C": experiment_c, "D": experiment_d, "E": experiment_e}


def run_all(lab, only: str = "ABCDE") -> dict:
    results = {}
    for name in only:
        results[name] = EXPERIMENTS[name](lab)
        print()
    return results


def main() -> int:
    ap = mode_args(__doc__)
    ap.add_argument("--only", default="A,B,C,D,E", help="comma-separated experiments, e.g. A,C")
    args = ap.parse_args()
    if args.record and args.mode != "live":
        print("--record only works with --mode live")
        return 2
    only = "".join(x.strip().upper() for x in args.only.split(",") if x.strip())
    with make_client(args.mode, REPLAY, record=args.record) as lab:
        print("   " + lab.label(f"{MODEL} requested; each experiment prints the model reported") + "\n")
        run_all(lab, only)
    return 0


if __name__ == "__main__":
    sys.exit(run(main))
