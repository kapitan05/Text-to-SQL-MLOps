from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch


class TestGenerateSql:
    def _make_sm_response(self, sql: str) -> dict[str, Any]:
        body = MagicMock()
        body.read.return_value = json.dumps({"sql": sql}).encode()
        return {"Body": body}

    def test_returns_sql_from_endpoint(self) -> None:
        from src.inference import generate_sql

        mock_client = MagicMock()
        mock_client.invoke_endpoint.return_value = self._make_sm_response(
            "SELECT COUNT(*) FROM t"
        )
        with patch("boto3.client", return_value=mock_client):
            result = generate_sql("How many rows?", "CREATE TABLE t (id INT);")

        assert result == "SELECT COUNT(*) FROM t"

    def test_invoke_endpoint_sends_question_and_context(self) -> None:
        from src.inference import generate_sql

        mock_client = MagicMock()
        mock_client.invoke_endpoint.return_value = self._make_sm_response("SELECT 1")
        with patch("boto3.client", return_value=mock_client):
            generate_sql("How many users?", "CREATE TABLE users (id INT);")

        kwargs = mock_client.invoke_endpoint.call_args.kwargs
        assert kwargs["ContentType"] == "application/json"
        body = json.loads(kwargs["Body"])
        assert body["question"] == "How many users?"
        assert "CREATE TABLE users" in body["context"]

    def test_retries_on_failure_then_raises(self) -> None:
        import pytest

        from src.inference import generate_sql

        mock_client = MagicMock()
        mock_client.invoke_endpoint.side_effect = RuntimeError("endpoint error")
        with patch("boto3.client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="endpoint error"):
                generate_sql("q", "CREATE TABLE t (id INT);")

        assert mock_client.invoke_endpoint.call_count == 3
