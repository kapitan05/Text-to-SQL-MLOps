from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

import pytest

from src.handler import lambda_handler

_BUCKET = "text2sql-failed-sql"
_CONTEXT = "CREATE TABLE orders (id INTEGER PRIMARY KEY, amount REAL);"
_SQL = "SELECT COUNT(*) FROM orders"


def _kinesis_event(query_id: str, question: str = "How many orders?") -> dict[str, Any]:
    payload = {"query_id": query_id, "question": question, "context": _CONTEXT}
    return {
        "Records": [
            {"kinesis": {"data": base64.b64encode(json.dumps(payload).encode()).decode()}}
        ]
    }


def _s3_key(query_id: str) -> str:
    today = datetime.now(UTC).strftime("%Y/%m/%d")
    return f"failed_sql/{today}/{query_id}.json"


@pytest.mark.integration
class TestHandlerIntegration:
    def test_success_path_writes_to_dynamodb(self, dynamodb_table: Any) -> None:
        query_id = "integ-handler-success-001"
        try:
            with patch("src.inference.generate_sql", return_value=_SQL):
                resp = lambda_handler(_kinesis_event(query_id), None)
            assert resp["statusCode"] == 200
            stored = dynamodb_table.get_item(Key={"query_id": query_id})["Item"]
            assert stored["sql"] == _SQL
            assert stored["status"] == "success"
            assert stored["query_id"] == query_id
        finally:
            dynamodb_table.delete_item(Key={"query_id": query_id})

    def test_failure_path_writes_to_s3(self, s3_client: Any) -> None:
        query_id = "integ-handler-failure-001"
        key = _s3_key(query_id)
        try:
            with patch("src.inference.generate_sql", side_effect=RuntimeError("boom")):
                resp = lambda_handler(_kinesis_event(query_id), None)
            assert resp["statusCode"] == 200
            body = json.loads(s3_client.get_object(Bucket=_BUCKET, Key=key)["Body"].read())
            assert body["query_id"] == query_id
            assert "boom" in body["error"]
        finally:
            s3_client.delete_object(Bucket=_BUCKET, Key=key)

    def test_success_path_does_not_write_to_s3(self, s3_client: Any, dynamodb_table: Any) -> None:
        query_id = "integ-handler-success-002"
        key = _s3_key(query_id)
        try:
            with patch("src.inference.generate_sql", return_value=_SQL):
                lambda_handler(_kinesis_event(query_id), None)
            with pytest.raises(s3_client.exceptions.NoSuchKey):
                s3_client.get_object(Bucket=_BUCKET, Key=key)
        finally:
            dynamodb_table.delete_item(Key={"query_id": query_id})

    def test_failure_path_does_not_write_to_dynamodb(self, dynamodb_table: Any, s3_client: Any) -> None:
        query_id = "integ-handler-failure-002"
        key = _s3_key(query_id)
        try:
            with patch("src.inference.generate_sql", side_effect=RuntimeError("fail")):
                lambda_handler(_kinesis_event(query_id), None)
            resp = dynamodb_table.get_item(Key={"query_id": query_id})
            assert "Item" not in resp
        finally:
            s3_client.delete_object(Bucket=_BUCKET, Key=key)
