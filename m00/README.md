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

TODO: filled in from the recorded run (date, model ID, SDK version, Python version).
