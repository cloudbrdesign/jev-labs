# Jev course labs

Hands-on labs for **Typed AI Decisions with Jev: System One Models for Engineers**, a course by
Cloud Brewery Academy. The videos are free on YouTube; this repo holds the code.

Independent course. Not affiliated with or endorsed by TypeSafe.

The labs build one project across the course: a support-inbox triage service for
**Lanternfield Outdoor Supply**, a fictional online outdoor-gear shop.

## Three ways to run every lab

| Mode | What it does | What you need |
|---|---|---|
| `--mode replay` (default) | Serves real Jev responses recorded on the course's machine. Every result is labelled `[RECORDED <date>]`. | Nothing but Python |
| `--mode live` | Calls Jev with your own key. | A TypeSafe account and `TYPESAFE_API_KEY` (usage is billed by TypeSafe; check their pages) |
| `--mode offline` | Scripted fake answers, labelled `[OFFLINE FAKE]`. Not Jev: for tests and CI only. | Nothing |

Replay only knows the requests the lab ships with. If you change a question or a ticket, run
that script in live mode.

## Start

```bash
python3 -m venv .venv && source .venv/bin/activate     # Python 3.10 or newer
pip install -r requirements.txt
python m00/check.py                                     # replay mode, no key needed
```

Then follow [m00/](m00/README.md). Each later module lives on its own branch
(`m01-first-decisions`, ...), so you can join at any module.

## Your key

Put it in your shell (`export TYPESAFE_API_KEY=...`) or in a `.env` file (copy `.env.example`).
`.env` is git-ignored. The labs never print the key and never write it to a file.
