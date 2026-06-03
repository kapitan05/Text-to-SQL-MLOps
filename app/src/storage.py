from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import boto3
from tenacity import retry, stop_after_attempt, wait_exponential

from src import metrics
from src.schemas import FailedSQLLog

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get("FAILED_SQL_BUCKET", "text2sql-failed-sql")


@lru_cache(maxsize=1)
def _get_client() -> S3Client:
    return boto3.client("s3")


_RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)


@_RETRY
def log_failed_sql(log: FailedSQLLog) -> None:
    now = datetime.now(UTC)
    key = f"failed_sql/{now.strftime('%Y/%m/%d')}/{log.query_id}.json"
    client: Any = _get_client()
    client.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=log.model_dump_json().encode(),
        ContentType="application/json",
    )
    logger.info("Logged failed SQL query_id=%s key=%s", log.query_id, key)
    try:
        metrics.current().s3_logs.labels(status="success").inc()
    except Exception:
        pass
