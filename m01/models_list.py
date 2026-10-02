"""M1 lab: the names you can send in `model`, next to the versioned ID that actually answered.

    python m01/models_list.py [--mode live|replay|offline]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from labkit.client import make_client, mode_args, run  # noqa: E402
from labkit.config import MODEL  # noqa: E402

HERE = Path(__file__).resolve().parent
REPLAY = HERE / "replay" / "models.jsonl"
DECISIONS = HERE.parent / "state" / "decisions.jsonl"


def main() -> int:
    args = mode_args(__doc__).parse_args()
    if args.record and args.mode != "live":
        print("--record only works with --mode live")
        return 2
    with make_client(args.mode, REPLAY, record=args.record) as lab:
        listing = lab.client.models.list().models
        print(lab.label(None).replace("model=None", "models list"))
        for m in listing:
            print(f"  {m.name:<14} released {m.release_date}  {m.description}")
    print(f"\nThe labs send model={MODEL} (a versioned ID, not an alias).")
    if DECISIONS.exists():
        rows = [json.loads(x) for x in DECISIONS.read_text().splitlines() if x.strip()]
        answered = sorted({r["model"] for r in rows if r.get("model")})
        print("Responses in state/decisions.jsonl were answered by:", ", ".join(answered) or "-")
    return 0


if __name__ == "__main__":
    sys.exit(run(main))
