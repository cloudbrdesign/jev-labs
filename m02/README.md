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

Recorded on 5 October 2026 on macOS with Python 3.12.2, typesafe-sdk 0.7.2, model `jev-1.13.0`
(16 live requests: 7 triage calls, 9 experiment calls). `m02/replay/*.jsonl` hold that run.

- `check.py`: 15 passed (replay); `pytest -q m02/tests`: 6 passed.
- Triage v2 matches our labels on 7 of 7 open tickets. LT-005 (boots) and LT-006 (sleeping bag),
  misrouted in Module 1, go to the Orders desk with `wrong_size` and `not_delivered`. LT-008 (gift
  card) goes to `other` with the probability split: other 0.53, billing 0.27, technical 0.20.
  Each triage request reported about 1,100 to 1,300 input tokens and about 250 output tokens.
- A (LT-002, stove won't light): levels "0", "1", "2" gave score 0.85 (0.80 on level 1);
  situation levels gave 1.85 (0.87 on "The product can't be used at all").
- B: the Noul "very frustrated?" gave LT-001 0.18, LT-003 0.63, LT-006 0.98; the frustration
  Score gave 0.22, 0.97 and 2.00 on its 0 to 3 scale.
- C: Module 1's options sent LT-005 to technical (0.65) and LT-006 to account (0.60);
  Module 2's options sent both to orders (1.00).
- D (LT-006, three orders): sleeping bag order 0.83, headlamp 0.04, daypack 0.03.
- E: one Noul "angry and asking for a refund?" gave LT-001 0.39 and LT-006 0.16. Asked
  separately: LT-001 angry 0.21, refund 0.97; LT-006 angry 0.98, refund 0.04. For LT-001 the
  combined question scored higher than one of its own conditions.
