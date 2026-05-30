"""
Load test for the local Lambda RIE.

Prerequisites:
    cd app
    docker compose up --build -d   # Lambda RIE + LocalStack must be running

Run:
    uv run python scripts/load_test.py
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any

import boto3

LAMBDA_URL = "http://localhost:8080/2015-03-31/functions/function/invocations"
DYNAMO_ENDPOINT = "http://localhost:4566"
TABLE_NAME = "query_results"

# ---------------------------------------------------------------------------
# Test cases — increasing SQL complexity
# ---------------------------------------------------------------------------

TEST_CASES: list[dict[str, str]] = [
    {
        "name": "simple count",
        "question": "How many orders are there?",
        "context": (
            "CREATE TABLE orders ("
            "id INTEGER PRIMARY KEY, amount REAL, status TEXT, created_at TEXT"
            ");"
        ),
    },
    {
        "name": "where filter",
        "question": "How many orders have status 'paid'?",
        "context": (
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, amount REAL, status TEXT);"
        ),
    },
    {
        "name": "group by + sum",
        "question": "What is the total amount for each status?",
        "context": (
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, amount REAL, status TEXT);"
        ),
    },
    {
        "name": "order by + limit",
        "question": "What are the 5 most expensive orders?",
        "context": (
            "CREATE TABLE orders ("
            "id INTEGER PRIMARY KEY, amount REAL, status TEXT, customer_id INTEGER"
            ");"
        ),
    },
    {
        "name": "having clause",
        "question": "Which customers have placed more than 3 orders?",
        "context": (
            "CREATE TABLE orders ("
            "id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL"
            ");"
        ),
    },
    {
        "name": "two-table join",
        "question": "List all orders with the customer name.",
        "context": (
            "CREATE TABLE orders ("
            "id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL, status TEXT"
            ");\n"
            "CREATE TABLE customers ("
            "id INTEGER PRIMARY KEY, name TEXT, email TEXT"
            ");"
        ),
    },
    {
        "name": "join + group by",
        "question": "What is the total amount spent by each customer?",
        "context": (
            "CREATE TABLE orders ("
            "id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL"
            ");\n"
            "CREATE TABLE customers ("
            "id INTEGER PRIMARY KEY, name TEXT"
            ");"
        ),
    },
    {
        "name": "subquery",
        "question": "Which products have a price above the average product price?",
        "context": (
            "CREATE TABLE products ("
            "id INTEGER PRIMARY KEY, name TEXT, price REAL, category TEXT"
            ");"
        ),
    },
]

# ---------------------------------------------------------------------------
# Invocation helpers
# ---------------------------------------------------------------------------


def _kinesis_event(query_id: str, question: str, context: str) -> bytes:
    payload = json.dumps(
        {"query_id": query_id, "question": question, "context": context}
    )
    data = base64.b64encode(payload.encode()).decode()
    return json.dumps({"Records": [{"kinesis": {"data": data}}]}).encode()


def _invoke(query_id: str, question: str, context: str) -> tuple[dict[str, Any], float]:
    body = _kinesis_event(query_id, question, context)
    req = urllib.request.Request(
        LAMBDA_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=600) as resp:
        result: dict[str, Any] = json.loads(resp.read())
    return result, time.monotonic() - t0


def _dynamo_get(table: Any, query_id: str) -> dict[str, Any] | None:
    resp = table.get_item(Key={"query_id": query_id})
    item: dict[str, Any] | None = resp.get("Item")
    return item


# ---------------------------------------------------------------------------
# Result record
# ---------------------------------------------------------------------------


@dataclass
class Result:
    name: str
    query_id: str
    elapsed: float
    status: str  # "success" | "failed→s3" | "error"
    sql: str = ""
    error: str = ""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    dynamodb = boto3.resource(
        "dynamodb",
        endpoint_url=DYNAMO_ENDPOINT,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    table = dynamodb.Table(TABLE_NAME)

    results: list[Result] = []

    print(f"\n{'─' * 80}")
    print(f"{'CASE':<22} {'TIME':>7}  {'STATUS':<12}  SQL")
    print(f"{'─' * 80}")

    for tc in TEST_CASES:
        query_id = str(uuid.uuid4())
        name: str = tc["name"]

        try:
            _, elapsed = _invoke(query_id, tc["question"], tc["context"])
        except urllib.error.URLError as exc:
            print(f"{name:<22} {'ERR':>7}  {'error':<12}  Lambda unreachable: {exc}")
            results.append(Result(name, query_id, 0.0, "error", error=str(exc)))
            continue

        item = _dynamo_get(table, query_id)

        if item:
            sql = str(item.get("sql", ""))
            r = Result(name, query_id, elapsed, "success", sql=sql)
            print(f"{name:<22} {elapsed:>6.1f}s  {'success':<12}  {sql}")
        else:
            # Routed to S3 failure path
            r = Result(name, query_id, elapsed, "failed→s3")
            print(
                f"{name:<22} {elapsed:>6.1f}s  {'failed→s3':<12}"
                "  (check S3 for error log)"
            )

        results.append(r)

    # Summary
    completed = [r for r in results if r.status != "error"]
    successes = [r for r in completed if r.status == "success"]
    failures = [r for r in completed if r.status == "failed→s3"]
    times = [r.elapsed for r in completed]

    print(f"\n{'─' * 80}")
    print(
        f"Total: {len(results)}"
        f"  |  Success: {len(successes)}"
        f"  |  Failed→S3: {len(failures)}"
    )
    if times:
        print(
            f"Timing — min: {min(times):.1f}s  max: {max(times):.1f}s  "
            f"mean: {sum(times) / len(times):.1f}s"
        )
    print(f"{'─' * 80}\n")


if __name__ == "__main__":
    main()
