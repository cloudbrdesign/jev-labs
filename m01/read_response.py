"""M1 lab: everything one response carries, printed field by field (ticket LT-006).

    python m01/read_response.py [--mode live|replay|offline]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from labkit.client import make_client, mode_args, run  # noqa: E402
from labkit.data import as_state, ticket  # noqa: E402
from labkit.show import response_footer  # noqa: E402

from triage_v1 import QUESTIONS, REPLAY  # noqa: E402  (same request as triage, so replay reuses it)


def describe(response) -> list[str]:
    lines = []
    for qid, a in response.answers.items():
        if a.type == "choice":
            probs = ", ".join(f"{k}={v:.2f}" for k, v in a.probabilities.items())
            lines.append(f"{qid} (choice): choice={a.choice}  confidence={a.confidence:.2f}  probabilities: {probs}")
        elif a.type == "score":
            probs = ", ".join(f"{k}={v:.2f}" for k, v in a.probabilities.items())
            legend = ", ".join(f"{k}={v}" for k, v in a.legend.items())
            lines.append(f"{qid} (score): score={a.score:.2f}  confidence={a.confidence:.2f}  probabilities: {probs}")
            lines.append(f"    legend: {legend}")
        else:
            lines.append(f"{qid} (noul): noul={a.noul:.2f}  (a Noul answer has no confidence field)")
    return lines


def main() -> int:
    args = mode_args(__doc__).parse_args()
    if args.record and args.mode != "live":
        print("--record only works with --mode live")
        return 2
    t = ticket("LT-006")
    with make_client(args.mode, REPLAY, record=args.record) as lab:
        r = lab.client.system_one(as_state(t), QUESTIONS)
        print(lab.label(r.model))
        print(f"{t['id']} '{t['subject']}'")
        for line in describe(r):
            print("  " + line)
        print("  " + response_footer(r))
    return 0


if __name__ == "__main__":
    sys.exit(run(main))
