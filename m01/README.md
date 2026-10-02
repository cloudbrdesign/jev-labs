# Module 1: first typed decisions

```bash
python m01/check.py                    # 13 numbered checks (replay mode)
python m01/triage_v1.py                # triage six inbox tickets; closed ones never reach the model
python m01/read_response.py            # every field of one response (ticket LT-006)
python m01/models_list.py              # model names you can send vs the versioned ID that answered
python m01/probes.py                   # two probes of known weak spots: negation and counting
pytest -q m01/tests                    # offline self-test
```

Add `--mode live` to call Jev with your own key (about 9 small requests for the whole module).

The probes print what the model returned. They are demonstrations, not tests: the checks only
verify the code around them.

## Runs

Recorded on 2 October 2026 on macOS with Python 3.12.2, typesafe-sdk 0.7.2, model `jev-1.13.0`
(11 live requests for M0 and M1 together). `m01/replay/*.jsonl` hold that run.

- `check.py`: 13 passed (replay); `pytest -q m01/tests`: 4 passed.
- Triage v1 sends LT-005 (boots a size too small) to Product support and LT-006 (missing sleeping
  bag) to the Account team: the `team` Choice offers only billing, technical and account, so the
  model must pick one of those. Lesson 1.4 discusses it; Module 2's lab adds `orders` and `other`.
- Probe A (negation, LT-005): refund 0.14, not_refund 0.79, sum 0.93.
- Probe B (counting, 7 items, our label 4 accessories): one Choice answered 4; one Noul per item,
  counted in code, gave 4. The counting weakness the docs describe did not show on this short list.
