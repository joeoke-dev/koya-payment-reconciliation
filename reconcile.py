#!/usr/bin/env python3
"""Payment reconciliation.

Reads payments.jsonl and works out how much money we actually collected.
Run:  python3 reconcile.py
"""
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

EPOCH = datetime.min.replace(tzinfo=timezone.utc)


def parse_ts(value):
    """Return an aware UTC datetime; unparseable values sort oldest."""
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError, OSError, OverflowError):
        return EPOCH


def parse_amount(value):
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return Decimal(0)


latest = {}  # txn_id -> (timestamp, event)

with open("payments.jsonl", encoding="utf-8-sig") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue  # unreadable line
        if not isinstance(event, dict):
            continue
        txn_id = event.get("txn_id")
        if txn_id is None or str(txn_id).strip() == "":
            continue  # no txn_id
        txn_id = str(txn_id).strip()
        ts = parse_ts(event.get("ts"))
        # latest attempt wins; on a tie, the later line in the file wins
        if txn_id not in latest or ts >= latest[txn_id][0]:
            latest[txn_id] = (ts, event)

total = Decimal(0)
count = 0
for ts, event in latest.values():
    if str(event.get("status", "")).strip().lower() == "success":
        total += parse_amount(event.get("amount"))
        count += 1

with open("expected.txt") as f:
    expected = int(f.read().strip())

if count != expected:
    print(f"Check failed: counted {count} successful payments, expected {expected}.")
    print("Something in the data isn't being handled the way the README describes.")
else:
    print(f"Check passed: {count} successful payments.")
    print(f"Your code: KOYA-{round(total)}")
