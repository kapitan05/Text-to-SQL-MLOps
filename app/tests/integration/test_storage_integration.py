from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

import pytest

from src.schemas import FailedSQLLog
from src.storage import log_failed_sql

_BUCKET = "text2sql-failed-sql"


def _make_log(query_id: str) -> FailedSQLLog:
    return FailedSQLLog(
        query_id=query_id,
        question="How many orders?",
        context="CREATE TABLE orders (id INTEGER PRIMARY KEY);",
        error="SQL syntax error",
        timestamp=datetime.now(UTC).isoformat(),
    )


def _expected_prefix(query_id: str) -> str:
    today = datetime.now(UTC).strftime("%Y/%m/%d")
    return f"failed_sql/{today}/{query_id}.json"


@pytest.mark.integration
class TestStorageIntegration:
    def test_log_failed_sql_creates_s3_object(self, s3_client: Any) -> None:
        log = _make_log("integ-s3-001")
        key = _expected_prefix("integ-s3-001")
        try:
            log_failed_sql(log)
            resp = s3_client.get_object(Bucket=_BUCKET, Key=key)
            assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
        finally:
            s3_client.delete_object(Bucket=_BUCKET, Key=key)

    def test_s3_object_key_matches_date_partition(self, s3_client: Any) -> None:
        log = _make_log("integ-s3-002")
        key = _expected_prefix("integ-s3-002")
        try:
            log_failed_sql(log)
            # key pattern: failed_sql/YYYY/MM/DD/<query_id>.json
            assert re.match(r"failed_sql/\d{4}/\d{2}/\d{2}/integ-s3-002\.json", key)
            s3_client.get_object(Bucket=_BUCKET, Key=key)  # raises if missing
        finally:
            s3_client.delete_object(Bucket=_BUCKET, Key=key)

    def test_s3_object_body_is_valid_json_with_all_fields(self, s3_client: Any) -> None:
        log = _make_log("integ-s3-003")
        key = _expected_prefix("integ-s3-003")
        try:
            log_failed_sql(log)
            body = s3_client.get_object(Bucket=_BUCKET, Key=key)["Body"].read()
            data = json.loads(body)
            assert data["query_id"] == "integ-s3-003"
            assert data["question"] == "How many orders?"
            assert data["error"] == "SQL syntax error"
            assert "timestamp" in data
            assert "context" in data
        finally:
            s3_client.delete_object(Bucket=_BUCKET, Key=key)
