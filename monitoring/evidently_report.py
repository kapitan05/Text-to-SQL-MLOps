#!/usr/bin/env python3
"""Daily Evidently data quality report.

Reads today's successful requests from DynamoDB, counts failures from S3,
generates an Evidently DataQualityPreset report, saves HTML to S3, and logs
key SLO metrics to MLflow.

Usage (from monitoring/):
    PYTHONPATH=. uv run python evidently_report.py --date 2026-05-30
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import tempfile
from datetime import UTC, date, datetime

import boto3
import mlflow
import polars as pl
from boto3.dynamodb.conditions import Attr
from evidently.metric_preset import DataQualityPreset
from evidently.report import Report

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "query_results")
FAILED_SQL_BUCKET = os.environ.get("FAILED_SQL_BUCKET", "text2sql-failed-sql")
MONITORING_BUCKET = os.environ.get("MONITORING_BUCKET", FAILED_SQL_BUCKET)
MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://0.0.0.0:5000")


def _scan_dynamo(target_date: date) -> pl.DataFrame:
    """Scan DynamoDB for items created on target_date.

    Items expire after 24h so expires_at ≈ created_at + 86400.
    We filter by expires_at in [day_start+86400, day_end+86400].
    """
    day_start = int(
        datetime(
            target_date.year, target_date.month, target_date.day, tzinfo=UTC
        ).timestamp()
    )
    exp_lo = day_start + 86400
    exp_hi = day_start + 2 * 86400

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)
    response = table.scan(FilterExpression=Attr("expires_at").between(exp_lo, exp_hi))
    items: list[dict[str, object]] = response.get("Items", [])  # type: ignore[assignment]

    if not items:
        logger.info("No DynamoDB items found for %s", target_date)
        return pl.DataFrame()

    rows = []
    for item in items:
        sql = str(item.get("sql", ""))
        try:
            result_rows_count = len(json.loads(str(item.get("rows", "[]"))))
        except (json.JSONDecodeError, TypeError):
            result_rows_count = 0
        rows.append(
            {
                "latency_ms": float(str(item.get("latency_ms", 0))),
                "sql_length": len(sql),
                "result_rows": result_rows_count,
            }
        )

    return pl.DataFrame(rows)


def _count_failed(target_date: date) -> int:
    s3 = boto3.client("s3")
    prefix = f"failed_sql/{target_date.strftime('%Y/%m/%d')}/"
    resp = s3.list_objects_v2(Bucket=FAILED_SQL_BUCKET, Prefix=prefix)
    return int(resp.get("KeyCount", 0))


def _upload_report(html: str, target_date: date) -> str:
    key = f"monitoring/reports/{target_date.strftime('%Y/%m/%d')}/drift_report.html"
    boto3.client("s3").put_object(
        Bucket=MONITORING_BUCKET,
        Key=key,
        Body=html.encode(),
        ContentType="text/html",
    )
    return key


def run(target_date: date) -> None:
    logger.info("Running Evidently report for %s", target_date)

    df = _scan_dynamo(target_date)
    failed_count = _count_failed(target_date)
    success_count = len(df)
    total = success_count + failed_count
    error_rate = failed_count / total if total > 0 else 0.0

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("text2sql-monitoring")

    with mlflow.start_run(run_name=f"monitoring-{target_date}"):
        mlflow.log_metrics(
            {
                "total_requests": float(total),
                "failed_requests": float(failed_count),
                "error_rate": error_rate,
            }
        )

        if df.is_empty():
            logger.warning(
                "No successful requests for %s — skipping report",
                target_date,
            )
            return

        p50 = df["latency_ms"].quantile(0.50) or 0.0
        p95 = df["latency_ms"].quantile(0.95) or 0.0
        p99 = df["latency_ms"].quantile(0.99) or 0.0
        mlflow.log_metrics(
            {
                "p50_latency_ms": p50,
                "p95_latency_ms": p95,
                "p99_latency_ms": p99,
                "avg_sql_length": df["sql_length"].mean() or 0.0,
                "avg_result_rows": df["result_rows"].mean() or 0.0,
            }
        )
        logger.info(
            "p50=%.0fms  p95=%.0fms  p99=%.0fms  error_rate=%.2f%%",
            p50,
            p95,
            p99,
            error_rate * 100,
        )

        report = Report(metrics=[DataQualityPreset()])
        report.run(current_data=df.to_pandas())

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
            report.save_html(f.name)
            tmp_path = f.name

        with open(tmp_path, encoding="utf-8") as f:
            html = f.read()

        s3_key = _upload_report(html, target_date)
        mlflow.log_param("report_s3_key", s3_key)
        logger.info("Report → s3://%s/%s", MONITORING_BUCKET, s3_key)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date",
        default=str(date.today()),
        help="YYYY-MM-DD (default: today)",
    )
    args = parser.parse_args()
    run(date.fromisoformat(args.date))


if __name__ == "__main__":
    main()
