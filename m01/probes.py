"""M1 lab: two probes of Jev 1.13's documented weak spots. Probes, not tests: we print what the
model returned and show the fix in code. Whatever the numbers are, they are reported as measured.

  A  Negation: a question and its negation as two Nouls in one request. Do they add up to 1?
     Fix: ask the question one way and derive the other side in code.
  B  Counting: one Choice "how many?" vs one Noul per item, counted in code.

    python m01/probes.py [--mode live|replay|offline]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typesafe_sdk import Choice, Noul  # noqa: E402

from labkit.client import make_client, mode_args, run  # noqa: E402
from labkit.data import as_state, ticket  # noqa: E402
from labkit.show import response_footer  # noqa: E402

HERE = Path(__file__).resolve().parent
REPLAY = HERE / "replay" / "probes.jsonl"
YES = 0.5  # our cut-off for counting a Noul as "yes" (a choice for this probe, not a rule)

NEGATION = {
    "refund": Noul(instructions="Is the customer asking for a refund?"),
    "not_refund": Noul(instructions="Is the customer asking for something other than a refund?"),
}

# Returned items from ticket LT-007, as a list. Our own labels: which items are accessories.
ITEMS = ["Ridgeline 2 tent", "Tent footprint", "Titanium tent pegs (pack of 6)",
         "Titanium tent pegs (pack of 6)", "Summit 30L daypack", "Daypack rain cover",
         "Trailblaze trekking poles"]
IS_ACCESSORY = [False, True, True, True, False, True, False]
ACCESSORY = "an accessory for another item in this list (it is only useful together with that item)"


def counting_questions():
    choice = {"how_many": Choice(
        instructions=f"How many entries in `items` are {ACCESSORY}?",
        criteria={str(n): None for n in range(len(ITEMS) + 1)})}
    per_item = {f"item_{i}": Noul(instructions=f"Is `items[{i}]` {ACCESSORY}?") for i in range(len(ITEMS))}
    return choice, per_item


def probe_negation(lab) -> dict:
    t = ticket("LT-005")
    r = lab.client.system_one(as_state(t), NEGATION)
    a, b = r.nouls["refund"].noul, r.nouls["not_refund"].noul
    print(lab.label(r.model))
    print(f"Probe A (negation) on {t['id']} '{t['body']}'")
    print(f"  refund={a:.2f}  not_refund={b:.2f}  sum={a + b:.2f}")
    print(f"  Fix in code: ask once (refund={a:.2f}); the other side is 1 - {a:.2f} = {1 - a:.2f}")
    print("  " + response_footer(r))
    return {"refund": a, "not_refund": b}


def probe_counting(lab) -> dict:
    choice_q, per_item_q = counting_questions()
    state = {"items": ITEMS}
    r1 = lab.client.system_one(state, choice_q)
    r2 = lab.client.system_one(state, per_item_q)
    truth = sum(IS_ACCESSORY)
    nouls = [r2.nouls[f"item_{i}"].noul for i in range(len(ITEMS))]
    counted = sum(n > YES for n in nouls)
    print(f"\nProbe B (counting) on {len(ITEMS)} returned items; our label: {truth} accessories")
    print(f"  B1 one Choice: answer={r1.choices['how_many'].choice}  confidence={r1.choices['how_many'].confidence:.2f}")
    for item, n, lab_ in zip(ITEMS, nouls, IS_ACCESSORY):
        print(f"     {n:.2f}  {'yes' if n > YES else 'no ':<3}  {item}  (our label: {'accessory' if lab_ else 'not'})")
    print(f"  B2 one Noul per item, counted in code (> {YES}): {counted}")
    print("  " + response_footer(r1))
    print("  " + response_footer(r2))
    return {"choice": r1.choices["how_many"].choice, "nouls": nouls, "counted": counted, "truth": truth}


def main() -> int:
    args = mode_args(__doc__).parse_args()
    if args.record and args.mode != "live":
        print("--record only works with --mode live")
        return 2
    with make_client(args.mode, REPLAY, record=args.record) as lab:
        probe_negation(lab)
        probe_counting(lab)
    return 0


if __name__ == "__main__":
    sys.exit(run(main))
