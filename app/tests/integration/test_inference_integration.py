from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest


def _make_sm_response(sql: str) -> dict[str, MagicMock]:
    body = MagicMock()
    body.read.return_value = json.dumps({"sql": sql}).encode()
    return {"Body": body}


def _make_sm_client(sql: str = "SELECT COUNT(*) FROM orders") -> MagicMock:
    client = MagicMock()
    client.invoke_endpoint.return_value = _make_sm_response(sql)
    return client


@pytest.mark.integration
class TestInferenceIntegration:
    def test_returns_sql_string(self, localstack_env: None) -> None:
        from src.inference import generate_sql

        client = _make_sm_client("SELECT COUNT(*) FROM orders")
        with patch("boto3.client", return_value=client):
            result = generate_sql("How many orders?", "CREATE TABLE orders (id INT);")

        assert result == "SELECT COUNT(*) FROM orders"

    def test_invoke_endpoint_uses_correct_endpoint_name(
        self, localstack_env: None
    ) -> None:
        from src.inference import generate_sql

        client = _make_sm_client()
        with patch("boto3.client", return_value=client):
            generate_sql("How many orders?", "CREATE TABLE orders (id INT);")

        kwargs = client.invoke_endpoint.call_args.kwargs
        assert kwargs["EndpointName"] == os.environ["SAGEMAKER_ENDPOINT_NAME"]

    def test_request_body_contains_question_and_context(
        self, localstack_env: None
    ) -> None:
        from src.inference import generate_sql

        client = _make_sm_client()
        ctx = "CREATE TABLE orders (id INT, amount REAL);"
        with patch("boto3.client", return_value=client):
            generate_sql("What is total amount?", ctx)

        kwargs = client.invoke_endpoint.call_args.kwargs
        assert kwargs["ContentType"] == "application/json"
        body = json.loads(kwargs["Body"])
        assert body["question"] == "What is total amount?"
        assert body["context"] == ctx

    def test_retries_three_times_on_transient_error(self, localstack_env: None) -> None:
        from src.inference import generate_sql

        client = MagicMock()
        client.invoke_endpoint.side_effect = RuntimeError("endpoint unavailable")
        with patch("boto3.client", return_value=client):
            with pytest.raises(RuntimeError, match="endpoint unavailable"):
                generate_sql("q", "CREATE TABLE t (id INT);")

        assert client.invoke_endpoint.call_count == 3
