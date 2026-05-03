import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


FUNNEL_ORDER = ["signup", "activation", "purchase", "renewal"]
ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
DATA_FILE = ROOT / "samples" / "events.json"
SHARED = ROOT.parent / "_shared_project_workbench"

if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

try:
    from local_llm import chat_json
except Exception:
    chat_json = None


def load_events(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def create_schema(db):
    db.execute(
        """
        create table if not exists events (
          event_id text primary key,
          account_id text,
          event_type text,
          timestamp text,
          status text
        )
        """
    )
    db.commit()


def ingest(db, events):
    create_schema(db)
    db.execute("delete from events")
    for event in events:
        db.execute(
            "insert into events(event_id, account_id, event_type, timestamp, status) values (?, ?, ?, ?, ?)",
            (event["event_id"], event["account_id"], event["event_type"], event["timestamp"], event["status"]),
        )
    db.commit()


def summarize(db):
    rows = list(db.execute("select account_id, event_type, timestamp, status from events"))
    account_events = defaultdict(set)
    status_counts = Counter()
    stage_counts = Counter()
    daily_counts = Counter()
    retry_accounts = set()

    for account_id, event_type, timestamp, status in rows:
        account_events[account_id].add(event_type)
        status_counts[status] += 1
        stage_counts[event_type] += 1
        daily_counts[timestamp[:10]] += 1
        if status != "ok":
            retry_accounts.add(account_id)

    accounts = []
    for account_id, event_types in sorted(account_events.items()):
        completed = [stage for stage in FUNNEL_ORDER if stage in event_types]
        next_stage = next((stage for stage in FUNNEL_ORDER if stage not in event_types), "complete")
        accounts.append({
            "account_id": account_id,
            "completed_stages": completed,
            "next_stage": next_stage,
            "completion_ratio": round(len(completed) / len(FUNNEL_ORDER), 2),
            "needs_followup": account_id in retry_accounts or next_stage != "complete",
        })

    total_events = len(rows)
    ok_events = status_counts.get("ok", 0)
    retry_events = total_events - ok_events

    return {
        "total_events": total_events,
        "total_accounts": len(account_events),
        "ok_events": ok_events,
        "retry_or_failed_events": retry_events,
        "quality_rate": round(ok_events / total_events, 3) if total_events else 0,
        "status_counts": dict(status_counts),
        "stage_counts": dict(stage_counts),
        "events_by_day": dict(sorted(daily_counts.items())),
        "accounts": accounts,
    }


def build_summary():
    db = sqlite3.connect(":memory:")
    events = load_events(DATA_FILE)
    ingest(db, events)
    summary = summarize(db)
    db.close()
    return events, summary


events, summary = build_summary()


def fallback_ai_insights():
    followups = sum(1 for account in summary["accounts"] if account["needs_followup"])
    return {
        "result": f"{summary['total_events']} CRM events processed across {summary['total_accounts']} accounts.",
        "recommendation": "Prioritize accounts stuck before purchase or renewal and review retry/failed events.",
        "decision": "Proceed with CRM pipeline monitoring and follow up on incomplete account journeys.",
        "executive_summary": f"Quality rate is {summary['quality_rate']:.1%}; {followups} accounts need follow-up.",
        "top_risks": [
            "Accounts may stall before purchase or renewal.",
            "Retry or failed events can hide customer journey problems.",
            "Small account groups should be monitored before scaling outreach automation."
        ],
        "operator_actions": [
            "Review accounts marked needs_followup.",
            "Investigate retry and failed event statuses.",
            "Use next_stage values to drive sales or lifecycle actions."
        ],
        "resume_signal": "Built a CRM event pipeline with deterministic funnel metrics and local-AI grounded analysis."
    }


def generate_ai_insights(model="google/gemma-4-e4b"):
    if chat_json is None:
        return fallback_ai_insights()

    prompt = f"""You are a senior CRM operations AI analyst.

Return ONLY valid JSON with:
- result
- recommendation
- decision
- executive_summary
- top_risks (array of 3)
- operator_actions (array of 3)
- resume_signal

Rules:
- use only the deterministic CRM summary
- no hallucinated metrics
- be concise and operator-friendly

CRM summary:
{json.dumps(summary, indent=2)}
"""
    try:
        ai = chat_json(prompt, model=model)
        if not isinstance(ai, dict):
            return fallback_ai_insights()
        return {
            "result": ai.get("result", ""),
            "recommendation": ai.get("recommendation", ""),
            "decision": ai.get("decision", ""),
            "executive_summary": ai.get("executive_summary", ""),
            "top_risks": ai.get("top_risks", []),
            "operator_actions": ai.get("operator_actions", []),
            "resume_signal": ai.get("resume_signal", "")
        }
    except Exception:
        return fallback_ai_insights()


ai_copilot = generate_ai_insights()


def chat_answer(question, model="google/gemma-4-e4b"):
    q = question.lower()
    fallback = {
        "answer": f"The pipeline processed {summary['total_events']} events across {summary['total_accounts']} accounts.",
        "evidence": f"Quality rate: {summary['quality_rate']:.1%}; status counts: {summary['status_counts']}",
        "next_action": "Review accounts that have incomplete funnel stages.",
        "recommendation": ai_copilot["recommendation"],
        "decision": ai_copilot["decision"],
        "risks": ai_copilot["top_risks"],
        "operator_actions": ai_copilot["operator_actions"]
    }

    incomplete_accounts = [a for a in summary["accounts"] if a["needs_followup"]]
    worst_accounts = sorted(summary["accounts"], key=lambda a: a["completion_ratio"])[:3]
    retry_statuses = {k: v for k, v in summary["status_counts"].items() if k != "ok"}

    if "risk" in q:
        fallback["answer"] = "The main risks are account funnel drop-off, retry/failed events, and incomplete lifecycle journeys."
        fallback["evidence"] = f"{len(incomplete_accounts)} accounts need follow-up; non-ok statuses: {retry_statuses}; stage counts: {summary['stage_counts']}"
        fallback["next_action"] = "Review the lowest completion accounts first, then investigate retry and failed statuses."
    elif "funnel" in q or "stage" in q or "drop" in q:
        fallback["answer"] = f"Funnel stage counts are {summary['stage_counts']}. Drop-off appears when accounts stop before the next stage."
        fallback["evidence"] = "Derived from deterministic event_type aggregation and account completion ratios."
        fallback["next_action"] = "Compare signup count against activation, purchase, and renewal counts to find the largest drop-off."
    elif "status" in q or "retry" in q or "fail" in q:
        fallback["answer"] = f"Status counts are {summary['status_counts']}. Non-ok statuses require operator review."
        fallback["evidence"] = f"Retry/failed event count is {summary['retry_or_failed_events']} out of {summary['total_events']} total events."
        fallback["next_action"] = "Investigate accounts connected to retry or failed events before using this data for automation."
    elif "account" in q or "follow" in q:
        needs = [a["account_id"] for a in incomplete_accounts]
        fallback["answer"] = f"Accounts needing follow-up: {', '.join(needs) if needs else 'none'}."
        fallback["evidence"] = "Accounts are flagged when they are incomplete or contain retry/failed events."
        fallback["next_action"] = "Prioritize accounts with the lowest completion ratio and any retry/failed event."
    elif "worst" in q or "lowest" in q or "compare" in q:
        fallback["answer"] = "The lowest-performing accounts are " + ", ".join(
            f"{a['account_id']} ({int(a['completion_ratio'] * 100)}%, next: {a['next_stage']})"
            for a in worst_accounts
        ) + "."
        fallback["evidence"] = "Accounts are ranked by completion_ratio from deterministic funnel progress."
        fallback["next_action"] = "Start with the lowest completion accounts and move them to their next_stage."

    if chat_json is None:
        return fallback

    prompt = f"""You are a senior CRM pipeline analyst.

Perform reasoning such as:
- identify worst-performing accounts
- explain funnel drop-offs
- compare account behaviors

Then answer.

Return ONLY valid JSON with:
- answer
- evidence
- next_action
- recommendation
- decision
- risks (array)
- operator_actions (array)

Question:
{question}

CRM summary:
{json.dumps(summary, indent=2)}

AI analyst:
{json.dumps(ai_copilot, indent=2)}
"""
    try:
        response = chat_json(prompt, model=model)
        if not isinstance(response, dict):
            return fallback
        return {
            "answer": response.get("answer", fallback["answer"]),
            "evidence": response.get("evidence", fallback["evidence"]),
            "next_action": response.get("next_action", fallback["next_action"]),
            "recommendation": response.get("recommendation", fallback["recommendation"]),
            "decision": response.get("decision", fallback["decision"]),
            "risks": response.get("risks", fallback["risks"]),
            "operator_actions": response.get("operator_actions", fallback["operator_actions"]),
        }
    except Exception:
        return fallback


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = "/index.html" if self.path == "/" else self.path
        if path == "/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "events": events,
                "summary": summary,
                "ai_copilot": ai_copilot
            }).encode())
            return

        file_path = WEB_ROOT / path.strip("/")
        if file_path.exists():
            self.send_response(200)
            self.end_headers()
            self.wfile.write(file_path.read_bytes())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/ask":
            length = int(self.headers.get("Content-Length", 0))
            question = self.rfile.read(length).decode()
            response = chat_answer(question)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())


def run_server():
    server = HTTPServer(("localhost", 8006), Handler)
    print("CRM Event Pipeline running at http://localhost:8006")
    server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="Ingest CRM events and generate funnel metrics.")
    parser.add_argument("--events", default=str(DATA_FILE))
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()

    if args.serve:
        run_server()
        return

    db = sqlite3.connect(":memory:")
    ingest(db, load_events(args.events))
    print(json.dumps(summarize(db), indent=2))


if __name__ == "__main__":
    main()
