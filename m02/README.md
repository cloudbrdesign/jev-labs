# Module 2: the three primitives

```bash
python m02/check.py                      # 15 numbered checks (replay mode)
python m02/triage_v2.py                  # triage v2: one request per open ticket, nine typed questions
python m02/experiments.py                # experiments A-E behind lessons 2.1 to 2.5
python m02/experiments.py --only C       # one experiment
pytest -q m02/tests                      # offline self-test
```

Add `--mode live` to call Jev with your own key (about 16 small requests for the whole module).

What changed since Module 1:

- `team` now offers `orders` and `other`, with structured descriptions (what / not_for /
  examples) for the two options that are easy to confuse, billing and orders.
- The state is an object: the ticket plus the customer's latest order from `data/orders.jsonl`
  (fictional records). Instructions point at fields with backticked paths such as `ticket.body`.
- One request asks every question the code might need. `order_issue` and `detail` are
  speculative: the code reads them only for orders and technical tickets.
- Code routes on the `team` Choice only. Nouls and the priority (normalised Scores, weights in
  `WEIGHTS`) are printed and logged with no thresholds. Module 3 is where thresholds are chosen.
- `m02/labels.json` holds the answers we expected, written before the recorded run.
  `check.py` reports how many routes match them; it doesn't grade the model.

The experiments print what the model returned. They are demonstrations, not tests.

## Runs

Not recorded yet.
