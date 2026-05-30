"""
AWS load test for the Text2SQL pipeline using real b-mc2/sql-create-context samples.

Sends N requests through API Gateway → Kinesis → Lambda → SageMaker → DynamoDB,
polls DynamoDB for results, and reports accuracy vs gold SQL.

Usage:
  export API_GW_URL=https://<id>.execute-api.us-east-1.amazonaws.com/<stage>
  export AWS_REGION=us-east-1              # default us-east-1
  export DYNAMODB_TABLE=query_results      # default query_results
  uv run python scripts/aws_load_test.py --samples 20 --workers 4
"""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

import boto3
import requests
from datasets import load_dataset

API_GW_URL = os.environ["API_GW_URL"].rstrip("/")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "query_results")

_dynamo = boto3.resource("dynamodb", region_name=AWS_REGION)
_table = _dynamo.Table(DYNAMODB_TABLE)


@dataclass
class TestCase:
    query_id: str
    question: str
    context: str
    gold_sql: str
    generated_sql: str = ""
    status: str = "pending"
    latency_ms: int = 0
    error: str = ""


@dataclass
class Report:
    total: int = 0
    success: int = 0
    failed: int = 0
    timeout: int = 0
    exact_match: int = 0
    cases: list[TestCase] = field(default_factory=list)

    def print_summary(self) -> None:
        print("\n" + "=" * 60)
        print(f"Total:       {self.total}")
        print(f"Success:     {self.success}  ({self.success / self.total * 100:.0f}%)")
        print(f"Failed:      {self.failed}")
        print(f"Timeout:     {self.timeout}")
        print(
            f"Exact match: {self.exact_match}  "
            f"({self.exact_match / max(self.success, 1) * 100:.0f}% of successful)"
        )
        avg_lat = sum(c.latency_ms for c in self.cases if c.latency_ms) / max(
            self.success, 1
        )
        print(f"Avg latency: {avg_lat:.0f} ms")
        print("=" * 60)

        print("\nSample results (first 5 successes):")
        shown = 0
        for c in self.cases:
            if c.status == "success" and shown < 5:
                match_marker = (
                    "✓" if c.generated_sql.strip() == c.gold_sql.strip() else "✗"
                )
                print(f"\n  Q: {c.question[:80]}")
                print(f"  Gold:  {c.gold_sql[:100]}")
                print(f"  Got:   {c.generated_sql[:100]}  {match_marker}")
                shown += 1

        failures = [c for c in self.cases if c.status != "success"]
        if failures:
            print("\nFirst failed case:")
            c = failures[0]
            print(f"  Q: {c.question[:80]}")
            print(f"  Status: {c.status}  Error: {c.error[:120]}")


def _send_request(case: TestCase) -> None:
    payload = {
        "query_id": case.query_id,
        "question": case.question,
        "context": case.context,
    }
    resp = requests.post(
        f"{API_GW_URL}/query",
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()


def _poll_dynamo(
    query_id: str, timeout_s: int = 120, interval_s: int = 5
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        resp = _table.get_item(Key={"query_id": query_id})
        item = resp.get("Item")
        if item:
            return dict(item)
        time.sleep(interval_s)
    raise TimeoutError(f"No DynamoDB result after {timeout_s}s")


def _run_case(case: TestCase) -> TestCase:
    try:
        _send_request(case)
        t0 = time.monotonic()
        item = _poll_dynamo(case.query_id)
        case.latency_ms = int((time.monotonic() - t0) * 1000)
        case.status = str(item.get("status", "unknown"))
        case.generated_sql = str(item.get("sql", ""))
    except TimeoutError:
        case.status = "timeout"
    except Exception as exc:
        case.status = "error"
        case.error = str(exc)
    return case


def _load_cases(n: int) -> list[TestCase]:
    ds: Any = load_dataset("b-mc2/sql-create-context", split="train")
    cases: list[TestCase] = []
    for row in ds.select(range(n)):
        cases.append(
            TestCase(
                query_id=f"load-{uuid.uuid4().hex[:12]}",
                question=str(row["question"]),
                context=str(row["context"]),
                gold_sql=str(row["answer"]),
            )
        )
    return cases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    print(f"Loading {args.samples} samples from b-mc2/sql-create-context …")
    cases = _load_cases(args.samples)
    print(
        f"Sending {len(cases)} requests to {API_GW_URL} with {args.workers} workers …\n"
    )

    report = Report(total=len(cases))

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_run_case, c): c for c in cases}
        for i, fut in enumerate(as_completed(futures), 1):
            c = fut.result()
            report.cases.append(c)
            if c.status == "success":
                report.success += 1
                if c.generated_sql.strip() == c.gold_sql.strip():
                    report.exact_match += 1
            elif c.status == "timeout":
                report.timeout += 1
            else:
                report.failed += 1
            icon = "." if c.status == "success" else "F"
            print(f"  [{i:>3}/{len(cases)}] {icon} {c.query_id}  status={c.status}")

    report.print_summary()

    with open("load_test_results.json", "w") as f:
        json.dump(
            [
                {
                    "query_id": c.query_id,
                    "question": c.question,
                    "gold_sql": c.gold_sql,
                    "generated_sql": c.generated_sql,
                    "status": c.status,
                    "latency_ms": c.latency_ms,
                    "error": c.error,
                }
                for c in report.cases
            ],
            f,
            indent=2,
        )
    print("\nFull results saved to load_test_results.json")


if __name__ == "__main__":
    main()
