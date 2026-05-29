from __future__ import annotations

import time
from decimal import Decimal
from typing import Any

import pytest

from src.dynamo import write_result
from src.schemas import DynamoResultItem


def _make_item(query_id: str) -> DynamoResultItem:
    return DynamoResultItem(
        query_id=query_id,
        sql="SELECT COUNT(*) FROM orders",
        rows="[]",
        latency_ms=123.45,
        status="success",
        expires_at=int(time.time()) + 86400,
    )


@pytest.mark.integration
class TestDynamoIntegration:
    def test_write_result_persists_item(self, dynamodb_table: Any) -> None:
        item = _make_item("integ-dynamo-001")
        try:
            write_result(item)
            resp = dynamodb_table.get_item(Key={"query_id": "integ-dynamo-001"})
            stored = resp["Item"]
            assert stored["query_id"] == "integ-dynamo-001"
            assert stored["sql"] == "SELECT COUNT(*) FROM orders"
            assert stored["status"] == "success"
        finally:
            dynamodb_table.delete_item(Key={"query_id": "integ-dynamo-001"})

    def test_latency_ms_stored_as_decimal(self, dynamodb_table: Any) -> None:
        item = _make_item("integ-dynamo-002")
        try:
            write_result(item)
            resp = dynamodb_table.get_item(Key={"query_id": "integ-dynamo-002"})
            stored = resp["Item"]
            assert isinstance(stored["latency_ms"], Decimal)
            assert stored["latency_ms"] == Decimal("123.45")
        finally:
            dynamodb_table.delete_item(Key={"query_id": "integ-dynamo-002"})

    def test_expires_at_is_in_the_future(self, dynamodb_table: Any) -> None:
        item = _make_item("integ-dynamo-003")
        try:
            write_result(item)
            resp = dynamodb_table.get_item(Key={"query_id": "integ-dynamo-003"})
            assert int(resp["Item"]["expires_at"]) > int(time.time())
        finally:
            dynamodb_table.delete_item(Key={"query_id": "integ-dynamo-003"})
