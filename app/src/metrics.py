from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from prometheus_client import CollectorRegistry, Counter, Histogram, push_to_gateway

logger = logging.getLogger(__name__)

PUSHGATEWAY_URL = os.environ.get("PUSHGATEWAY_URL", "http://localhost:9091")

_LATENCY_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)


@dataclass
class InvocationMetrics:
    registry: CollectorRegistry
    requests_total: Counter
    request_duration: Histogram
    inference_duration: Histogram
    inference_retries: Counter
    sql_executions: Counter
    dynamo_writes: Counter
    s3_logs: Counter
    kinesis_records: Counter
    batch_size: Histogram
    result_rows: Histogram

    def push(self) -> None:
        try:
            push_to_gateway(
                PUSHGATEWAY_URL, job="text2sql-lambda", registry=self.registry
            )
        except Exception:
            logger.warning("metrics push failed", exc_info=True)


_current: InvocationMetrics | None = None


def begin() -> InvocationMetrics:
    """Create a fresh per-invocation registry. Call once per lambda_handler call."""
    global _current
    reg = CollectorRegistry()
    _current = InvocationMetrics(
        registry=reg,
        requests_total=Counter(
            "text2sql_requests_total",
            "Total requests by outcome",
            ["status"],
            registry=reg,
        ),
        request_duration=Histogram(
            "text2sql_request_duration_seconds",
            "End-to-end request latency",
            buckets=_LATENCY_BUCKETS,
            registry=reg,
        ),
        inference_duration=Histogram(
            "text2sql_inference_duration_seconds",
            "SageMaker invocation latency",
            buckets=_LATENCY_BUCKETS,
            registry=reg,
        ),
        inference_retries=Counter(
            "text2sql_inference_retries_total",
            "SageMaker retry attempts by attempt number that failed",
            ["attempt"],
            registry=reg,
        ),
        sql_executions=Counter(
            "text2sql_sql_executions_total",
            "SQL executions by outcome",
            ["status"],
            registry=reg,
        ),
        dynamo_writes=Counter(
            "text2sql_dynamo_writes_total",
            "DynamoDB put_item calls by outcome",
            ["status"],
            registry=reg,
        ),
        s3_logs=Counter(
            "text2sql_s3_logs_total",
            "S3 failed-SQL log writes by outcome",
            ["status"],
            registry=reg,
        ),
        kinesis_records=Counter(
            "text2sql_kinesis_records_total",
            "Kinesis records processed by decode status",
            ["status"],
            registry=reg,
        ),
        batch_size=Histogram(
            "text2sql_batch_size",
            "Kinesis records per Lambda invocation",
            buckets=(1, 2, 5, 10, 20, 50),
            registry=reg,
        ),
        result_rows=Histogram(
            "text2sql_result_rows",
            "SQL query result row count",
            buckets=(1, 5, 10, 50, 100, 500),
            registry=reg,
        ),
    )
    return _current


def current() -> InvocationMetrics:
    """Return the active invocation's metrics. Raises if begin() was not called."""
    if _current is None:
        raise RuntimeError("metrics.begin() not called for this invocation")
    return _current
