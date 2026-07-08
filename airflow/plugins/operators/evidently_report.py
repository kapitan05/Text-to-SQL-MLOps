from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import UTC, date, datetime
from typing import Any

import boto3
import mlflow
import polars as pl
from airflow.models import BaseOperator
from airflow.utils.context import Context
from boto3.dynamodb.conditions import Attr
from evidently.metric_preset import DataQualityPreset
from evidently.report import Report

logger = logging.getLogger(__name__)

_TABLE = os.environ.get("DYNAMODB_TABLE", "query_results")
_FAILED_BUCKET = os.environ.get("FAILED_SQL_BUCKET", "text2sql-failed-sql")
_MONITORING_BUCKET = os.environ.get("MONITORING_BUCKET", _FAILED_BUCKET)
_MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")


def _scan_dynamo(target_date: date) -> pl.DataFrame:
    day_start = int(
        datetime(
            target_date.year, target_date.month, target_date.day, tzinfo=UTC
        ).timestamp()
    )
    exp_lo = day_start + 86400
    exp_hi = day_start + 2 * 86400

    table = boto3.resource("dynamodb").Table(_TABLE)
    items: list[dict[str, Any]] = table.scan(
        FilterExpression=Attr("expires_at").between(exp_lo, exp_hi)
    ).get("Items", [])

    if not items:
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
    prefix = f"failed_sql/{target_date.strftime('%Y/%m/%d')}/"
    resp = boto3.client("s3").list_objects_v2(Bucket=_FAILED_BUCKET, Prefix=prefix)
    return int(resp.get("KeyCount", 0))


def _upload_report(html: str, target_date: date) -> str:
    key = f"monitoring/reports/{target_date.strftime('%Y/%m/%d')}/drift_report.html"
    boto3.client("s3").put_object(
        Bucket=_MONITORING_BUCKET,
        Key=key,
        Body=html.encode(),
        ContentType="text/html",
    )
    return key


class EvidentlyReportOperator(BaseOperator):
    template_fields = ("ds",)

    def __init__(self, *, ds: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.ds = ds

    def execute(self, context: Context) -> None:
        target_date = date.fromisoformat(self.ds)
        logger.info("Running Evidently report for %s", target_date)

        df = _scan_dynamo(target_date)
        failed_count = _count_failed(target_date)
        success_count = len(df)
        total = success_count + failed_count
        error_rate = failed_count / total if total > 0 else 0.0

        mlflow.set_tracking_uri(_MLFLOW_URI)
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
                    "No successful requests for %s — skipping Evidently report",
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

            with tempfile.NamedTemporaryFile(
                suffix=".html", delete=False, mode="w"
            ) as f:
                report.save_html(f.name)
                tmp_path = f.name

            with open(tmp_path, encoding="utf-8") as f:
                html = f.read()

            s3_key = _upload_report(html, target_date)
            mlflow.log_param("report_s3_key", s3_key)
            logger.info("Report → s3://%s/%s", _MONITORING_BUCKET, s3_key)
