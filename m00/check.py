"""M0 checks. Run from the repo root with the venv active:

    python m00/check.py                  # replay mode (no key needed)
    python m00/check.py --mode live      # also checks your key with one models call
"""
from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from labkit.config import MODEL  # noqa: E402
from labkit.env import api_key  # noqa: E402

REPLAY = ROOT / "m00" / "replay" / "first_call.jsonl"
results: list[tuple[int, str, str, str]] = []


def check(n: int, name: str, ok: bool | None, note: str = "") -> None:
    status = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
    results.append((n, name, status, note))
    print(f"{n:>2} {status:4}  {name}" + (f"  ({note})" if note else ""))


def pins() -> dict[str, str]:
    out = {}
    for line in (ROOT / "requirements.txt").read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if "==" in line:
            name, ver = line.split("==", 1)
            out[name.strip().lower()] = ver.strip()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("live", "replay", "offline"), default="replay")
    mode = ap.parse_args().mode
    print(f"M0 checks, mode={mode}\n")

    check(1, "Python is 3.10 or newer", sys.version_info >= (3, 10), sys.version.split()[0])
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    check(2, "Running inside a virtual environment", in_venv, sys.prefix)

    wrong = []
    for name, ver in pins().items():
        try:
            have = md.version(name)
        except md.PackageNotFoundError:
            have = "missing"
        if have != ver:
            wrong.append(f"{name} {have} != {ver}")
    check(3, "Installed packages match requirements.txt", not wrong, "; ".join(wrong[:3]))

    ignored = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=ROOT).returncode == 0
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", ".env"], cwd=ROOT,
                             capture_output=True).returncode == 0
    check(4, ".env is git-ignored and not tracked", ignored and not tracked)

    key = api_key()
    if mode == "live":
        check(5, "TYPESAFE_API_KEY is set", bool(key), "value not shown")
    else:
        check(5, "TYPESAFE_API_KEY is set", None, "not needed in " + mode + " mode")

    if mode == "live" and key:
        from typesafe_sdk import TypeSafeClient, TypeSafeError
        try:
            with TypeSafeClient(api_key=key, model=MODEL) as c:
                names = [m.name for m in c.models.list().models]
            check(6, "Key accepted (models list)", bool(names), ", ".join(names))
        except TypeSafeError as e:
            check(6, "Key accepted (models list)", False, type(e).__name__)
    else:
        check(6, "Key accepted (models list)", None, "live mode only")

    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "m00/tests"], cwd=ROOT,
                       capture_output=True, text=True)
    check(7, "Offline self-test passes", r.returncode == 0, r.stdout.strip().splitlines()[-1] if r.stdout else "")

    entries = []
    if REPLAY.exists():
        entries = [json.loads(x) for x in REPLAY.read_text().splitlines() if x.strip()]
    labelled = bool(entries) and all(e.get("recorded_utc") and e.get("sdk_version") for e in entries)
    check(8, "Replay file present and labelled (date, SDK version)", labelled,
          f"{len(entries)} entries" if entries else "not recorded yet")

    calls = [e for e in entries if e.get("path") == "/v1/systemone"]
    model = calls[-1]["model"] if calls else None
    check(9, "Recorded call reports a versioned model ID", bool(model and re.fullmatch(r"jev-\d+\.\d+\.\d+", model)),
          str(model))

    usage = (calls[-1].get("response") or {}).get("usage", {}) if calls else {}
    ok_usage = bool(calls) and all(v is None or isinstance(v, int) for v in usage.values())
    check(10, "Usage fields are integers or absent", ok_usage, json.dumps(usage) if usage else "")

    if mode == "live" and key:
        files = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT,
                               capture_output=True, text=True).stdout.split()
        leaked = [f for f in files if (ROOT / f).is_file() and key in (ROOT / f).read_text(errors="ignore")]
        check(11, "No file in the working tree contains your key", not leaked, ", ".join(leaked))
    else:
        check(11, "No file in the working tree contains your key", None, "live mode only")

    raw = REPLAY.read_text() if REPLAY.exists() else ""
    check(12, "Replay file stores no authorization header", "authorization" not in raw.lower())

    failed = [n for n, _, s, _ in results if s == "FAIL"]
    print(f"\n{sum(s == 'PASS' for _, _, s, _ in results)} passed, {len(failed)} failed, "
          f"{sum(s == 'SKIP' for _, _, s, _ in results)} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
