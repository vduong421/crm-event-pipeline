# CRM Event Pipeline

A small backend/data project that ingests CRM events, stores them in SQLite, and produces funnel metrics.

## Why It Matches CRM / Platform Jobs

- TikTok Global CRM-style transaction and event workflow
- Shows event ingestion, schema design, aggregation, and reporting
- Useful for backend, data platform, and product analytics roles

## Features

- JSON event ingestion
- SQLite event storage
- Funnel metrics by account
- Event latency and status summaries
- JSON report output

## Run

```powershell
python app.py --events samples/events.json
```

## Engineering Impact
- Built a Python CRM event pipeline that ingests JSON events, stores them in SQLite, and generates account-level funnel metrics.
- Modeled customer lifecycle events such as signup, activation, purchase, and renewal for backend/product analytics reporting.
- Produced structured summaries for transaction status, conversion progress, and event counts.

## Project Workbench

Launch the production-style desktop workbench with:

```powershell
launch-workbench.bat
```

What it adds:

- Local-first AI copilot using `google/gemma-4-e4b` by default
- Operator-focused workbench for reviewing real project inputs and outputs
- System design, production-impact, and operational brief generation on demand
- Grounded responses based on this project's README, sample files, and deterministic outputs

