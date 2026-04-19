import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path


FUNNEL_ORDER = ["signup", "activation", "purchase", "renewal"]


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
    account_events = defaultdict(set)
    status_counts = defaultdict(int)
    for account_id, event_type, status in db.execute("select account_id, event_type, status from events"):
        account_events[account_id].add(event_type)
        status_counts[status] += 1

    accounts = []
    for account_id, event_types in sorted(account_events.items()):
        completed = [stage for stage in FUNNEL_ORDER if stage in event_types]
        next_stage = next((stage for stage in FUNNEL_ORDER if stage not in event_types), "complete")
        accounts.append({
            "account_id": account_id,
            "completed_stages": completed,
            "next_stage": next_stage,
            "completion_ratio": round(len(completed) / len(FUNNEL_ORDER), 2),
        })

    return {
        "total_events": sum(status_counts.values()),
        "status_counts": dict(status_counts),
        "accounts": accounts,
    }


def main():
    parser = argparse.ArgumentParser(description="Ingest CRM events and generate funnel metrics.")
    parser.add_argument("--events", required=True)
    args = parser.parse_args()

    db = sqlite3.connect(":memory:")
    ingest(db, load_events(args.events))
    print(json.dumps(summarize(db), indent=2))


if __name__ == "__main__":
    main()
