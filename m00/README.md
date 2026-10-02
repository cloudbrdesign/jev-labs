# Module 0: setup and your first call

```bash
python m00/check.py                    # 12 numbered checks (replay mode)
python m00/first_call.py               # one Noul on ticket LT-001, replayed
python m00/first_call.py --mode live   # the same call with your key (2 small requests)
pytest -q m00/tests                    # offline self-test: the real SDK against a scripted fake
```

`first_call.py` checks your key with a models list call, asks one Noul about ticket LT-001,
and prints the answer, the versioned model ID that answered and the token usage.

## Runs

Recorded on 2 October 2026 on macOS with Python 3.12.2, typesafe-sdk 0.7.2, model `jev-1.13.0`
(the versioned ID every response reported). `m00/replay/first_call.jsonl` holds that run.

| Check | Replay | Live |
|---|---|---|
| `python m00/check.py` | 9 passed, 3 skipped (key checks are live only) | 12 passed |
| `first_call.py` | refund_requested noul 0.97; 334 input / 21 output tokens | same response (it is the one replay serves) |
| `pytest -q m00/tests` | 7 passed | 7 passed |
