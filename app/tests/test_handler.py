from __future__ import annotations

import base64
import json
from typing import Any
from unittest.mock import patch

from src.handler import lambda_handler


def _kinesis_event(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "Records": [
            {"kinesis": {"data": base64.b64encode(json.dumps(r).encode()).decode()}}
            for r in records
        ]
    }


_VALID_REQUEST = {
    "query_id": "qid-abc",
    "question": "How many orders?",
    "context": "CREATE TABLE orders (id INTEGER PRIMARY KEY, amount REAL);",
}

_GENERATED_SQL = "SELECT COUNT(*) FROM orders"


class TestLambdaHandlerSuccess:
    def test_happy_path_calls_write_result(self) -> None:
        with (
            patch("src.inference.generate_sql", return_value=_GENERATED_SQL),
            patch("src.dynamo.write_result") as mock_write,
            patch("src.storage.log_failed_sql") as mock_log,
        ):
            resp = lambda_handler(_kinesis_event([_VALID_REQUEST]), None)

        assert resp["statusCode"] == 200
        mock_write.assert_called_once()
        mock_log.assert_not_called()

    def test_result_item_has_correct_query_id(self) -> None:
        with (
            patch("src.inference.generate_sql", return_value=_GENERATED_SQL),
            patch("src.dynamo.write_result") as mock_write,
            patch("src.storage.log_failed_sql"),
        ):
            lambda_handler(_kinesis_event([_VALID_REQUEST]), None)

        item = mock_write.call_args.args[0]
        assert item.query_id == "qid-abc"
        assert item.sql == _GENERATED_SQL
        assert item.status == "success"
        assert item.expires_at > 0

    def test_processes_multiple_records(self) -> None:
        r2 = {**_VALID_REQUEST, "query_id": "qid-xyz"}
        with (
            patch("src.inference.generate_sql", return_value=_GENERATED_SQL),
            patch("src.dynamo.write_result") as mock_write,
            patch("src.storage.log_failed_sql"),
        ):
            lambda_handler(_kinesis_event([_VALID_REQUEST, r2]), None)

        assert mock_write.call_count == 2


class TestLambdaHandlerFailure:
    def test_inference_failure_routes_to_storage(self) -> None:
        with (
            patch("src.inference.generate_sql", side_effect=RuntimeError("model fail")),
            patch("src.dynamo.write_result") as mock_write,
            patch("src.storage.log_failed_sql") as mock_log,
        ):
            resp = lambda_handler(_kinesis_event([_VALID_REQUEST]), None)

        assert resp["statusCode"] == 200
        mock_write.assert_not_called()
        mock_log.assert_called_once()
        log = mock_log.call_args.args[0]
        assert log.query_id == "qid-abc"
        assert "model fail" in log.error

    def test_invalid_sql_routes_to_storage(self) -> None:
        with (
            patch("src.inference.generate_sql", return_value="NOT VALID SQL;;;"),
            patch("src.dynamo.write_result") as mock_write,
            patch("src.storage.log_failed_sql") as mock_log,
        ):
            lambda_handler(_kinesis_event([_VALID_REQUEST]), None)

        mock_write.assert_not_called()
        mock_log.assert_called_once()


class TestLambdaHandlerEdgeCases:
    def test_empty_event_returns_200(self) -> None:
        resp = lambda_handler({"Records": []}, None)
        assert resp["statusCode"] == 200
        assert "no records" in resp["body"]

    def test_malformed_record_is_skipped(self) -> None:
        bad_event = {
            "Records": [{"kinesis": {"data": base64.b64encode(b"not json").decode()}}]
        }
        with (
            patch("src.inference.generate_sql") as mock_gen,
            patch("src.dynamo.write_result"),
            patch("src.storage.log_failed_sql"),
        ):
            resp = lambda_handler(bad_event, None)

        assert resp["statusCode"] == 200
        mock_gen.assert_not_called()
