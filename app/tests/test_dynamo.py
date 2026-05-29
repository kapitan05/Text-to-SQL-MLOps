from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.dynamo import write_result
from src.schemas import DynamoResultItem


def _make_item(**overrides: object) -> DynamoResultItem:
    defaults: dict[str, object] = {
        "query_id": "qid-001",
        "sql": "SELECT 1",
        "rows": "[]",
        "latency_ms": 42.0,
        "status": "success",
        "expires_at": 9999999999,
    }
    defaults.update(overrides)
    return DynamoResultItem(**defaults)  # type: ignore[arg-type]


class TestWriteResult:
    def test_calls_put_item_with_correct_shape(self) -> None:
        mock_table = MagicMock()
        with patch("src.dynamo._get_table", return_value=mock_table):
            item = _make_item()
            write_result(item)

        mock_table.put_item.assert_called_once()
        kwargs = mock_table.put_item.call_args.kwargs
        assert kwargs["Item"]["query_id"] == "qid-001"
        assert kwargs["Item"]["status"] == "success"
        assert "expires_at" in kwargs["Item"]

    def test_put_item_contains_all_fields(self) -> None:
        mock_table = MagicMock()
        with patch("src.dynamo._get_table", return_value=mock_table):
            item = _make_item(sql="SELECT COUNT(*) FROM t", rows='[{"n": 1}]')
            write_result(item)

        item_written = mock_table.put_item.call_args.kwargs["Item"]
        assert item_written["sql"] == "SELECT COUNT(*) FROM t"
        assert item_written["rows"] == '[{"n": 1}]'
        from decimal import Decimal
        assert isinstance(item_written["latency_ms"], Decimal)

    def test_retries_on_failure_then_raises(self) -> None:
        mock_table = MagicMock()
        mock_table.put_item.side_effect = Exception("DynamoDB unavailable")
        with patch("src.dynamo._get_table", return_value=mock_table):
            import pytest

            with pytest.raises(Exception, match="DynamoDB unavailable"):
                write_result(_make_item())
        assert mock_table.put_item.call_count == 3
