from __future__ import annotations

import json
import logging
import time
from contextlib import closing
from datetime import UTC, datetime, timedelta
from typing import Any

from src import dynamo, inference, metrics, storage
from src.executor import create_db_from_ddl, execute_sql
from src.kinesis import decode_records
from src.schemas import DynamoResultItem, FailedSQLLog

logger = logging.getLogger(__name__)

_TTL_HOURS = 24


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    m = metrics.begin()
    try:
        requests = decode_records(event)
        if not requests:
            return {"statusCode": 200, "body": "no records"}

        m.batch_size.observe(len(requests))

        for req in requests:
            t0 = time.monotonic()
            try:
                sql = inference.generate_sql(req.question, req.context)
                with closing(create_db_from_ddl(req.context)) as conn:
                    rows = execute_sql(conn, sql)
                latency_ms = (time.monotonic() - t0) * 1000
                m.requests_total.labels(status="success").inc()
                m.request_duration.observe(latency_ms / 1000)
                m.result_rows.observe(len(rows))
                expires_at = int(
                    (datetime.now(UTC) + timedelta(hours=_TTL_HOURS)).timestamp()
                )
                dynamo.write_result(
                    DynamoResultItem(
                        query_id=req.query_id,
                        sql=sql,
                        rows=json.dumps(rows),
                        latency_ms=latency_ms,
                        status="success",
                        expires_at=expires_at,
                    )
                )
            except Exception:
                m.requests_total.labels(status="failure").inc()
                m.request_duration.observe(time.monotonic() - t0)
                logger.exception("Failed processing query_id=%s", req.query_id)
                storage.log_failed_sql(
                    FailedSQLLog(
                        query_id=req.query_id,
                        question=req.question,
                        context=req.context,
                        error=_last_exc_msg(),
                        timestamp=datetime.now(UTC).isoformat(),
                    )
                )

        return {"statusCode": 200, "body": f"processed {len(requests)} records"}
    finally:
        m.push()


def _last_exc_msg() -> str:
    import sys

    exc = sys.exc_info()[1]
    return str(exc) if exc else "unknown error"
