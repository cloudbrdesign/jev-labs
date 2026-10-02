"""M0 lab: your first Jev call.

    python m00/first_call.py                   # replay: real recorded responses, no key needed
    python m00/first_call.py --mode live       # your own key (TYPESAFE_API_KEY)
    python m00/first_call.py --mode offline    # scripted fake, no network
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typesafe_sdk import Noul  # noqa: E402

from labkit.client import make_client, mode_args, run  # noqa: E402
from labkit.data import as_state, ticket  # noqa: E402
from labkit.env import key_status  # noqa: E402
from labkit.show import response_footer  # noqa: E402

REPLAY = Path(__file__).resolve().parent / "replay" / "first_call.jsonl"
QUESTION = Noul(instructions="Does this message ask for a refund or for a charge to be reversed?")


def main() -> int:
    args = mode_args(__doc__).parse_args()
    if args.record and args.mode != "live":
        print("--record only works with --mode live")
        return 2
    print(f"TYPESAFE_API_KEY: {key_status()}  (the value is never printed)")
    with make_client(args.mode, REPLAY, record=args.record) as lab:
        names = [m.name for m in lab.client.models.list().models]
        print("Key check: models available ->", ", ".join(names))
        t = ticket("LT-001")
        response = lab.client.system_one(as_state(t), {"refund_requested": QUESTION})
        print(lab.label(response.model))
        print(f"{t['id']} '{t['subject']}'")
        print(f"refund_requested: noul = {response.nouls['refund_requested'].noul}")
        print(response_footer(response))
    return 0


if __name__ == "__main__":
    sys.exit(run(main))
