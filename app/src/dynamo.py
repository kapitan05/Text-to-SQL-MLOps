from __future__ import annotations

import logging
import os
from decimal import Decimal
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import boto3
from tenacity import retry, stop_after_attempt, wait_exponential

from src import metrics
from src.schemas import DynamoResultItem

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

logger = logging.getLogger(__name__)

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "query_results")


@lru_cache(maxsize=1)
def _get_table() -> Table:
    dynamodb: Any = boto3.resource("dynamodb")
    return dynamodb.Table(TABLE_NAME)  # type: ignore[no-any-return]


_RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)


@_RETRY
def write_result(item: DynamoResultItem) -> None:
    data = item.model_dump()
    data["latency_ms"] = Decimal(str(data["latency_ms"]))
    _get_table().put_item(Item=data)
    logger.info("Wrote result for query_id=%s", item.query_id)
    try:
        metrics.current().dynamo_writes.labels(status="success").inc()
    except Exception:
        pass
