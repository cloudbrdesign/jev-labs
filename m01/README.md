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

TODO: filled in from the recorded run (date, model ID, SDK version, Python version).
