# CRM Event Pipeline

CRM Event Pipeline is a local analytics tool that ingests CRM lifecycle events, computes funnel metrics, detects account follow-up signals, and uses a local AI analyst to explain customer pipeline movement.

The project models a real operational analytics workflow where deterministic metrics drive the dashboard and AI converts those metrics into clear account actions.

## What It Does

- Loads CRM events from JSON.
- Groups events by account and lifecycle stage.
- Computes funnel counts, conversion movement, and stalled accounts.
- Identifies follow-up opportunities and account health signals.
- Serves a browser dashboard for quick review.
- Adds AI-generated account and pipeline interpretation.

## AI Features

- Local AI analyst explains funnel health and follow-up priorities.
- AI summary converts raw lifecycle counts into operator-ready actions.
- Recommendations are grounded in deterministic event metrics.
- Browser UI shows operational metrics and AI analysis together.

## Architecture

```text
samples/events.json
        |
        v
CRM event parser -> account grouping -> funnel metrics -> follow-up flags
        |
        v
Local AI analyst -> pipeline summary + next actions
        |
        v
Browser dashboard
```

## Run

```powershell
run.bat
```

## Local AI Setup

- Designed for a local OpenAI-compatible model server.
- Default project model: `google/gemma-4-e4b`.
- Deterministic dashboard metrics continue to work without AI.

## Main Files

- `app.py` - event processing and AI insight generation.
- `web/index.html` - dashboard UI.
- `samples/events.json` - CRM event dataset.
- `agents/Agent.md` - AI analyst instructions.

## Output

The dashboard shows funnel stage counts, account health indicators, recommended follow-up actions, and a local AI analyst summary.
