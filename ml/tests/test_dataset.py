from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from data.dataset import DatasetConfig, SQLExample, format_example
from modeling.prompts import SYSTEM_PROMPT, build_prompt


class TestSQLExample:
    def test_fields_required(self) -> None:
        ex = SQLExample(
            question="How many users?",
            context="CREATE TABLE users (id INTEGER);",
            answer="SELECT COUNT(*) FROM users",
        )
        assert ex.question == "How many users?"

    def test_missing_field_raises(self) -> None:
        with pytest.raises(Exception):
            SQLExample(question="q", context="c")  # type: ignore[call-arg]


class TestPrompts:
    def test_build_prompt_contains_all_parts(self) -> None:
        prompt = build_prompt(
            "CREATE TABLE t (id INT);", "Count rows", "SELECT COUNT(*) FROM t"
        )
        assert SYSTEM_PROMPT in prompt
        assert "CREATE TABLE t" in prompt
        assert "Count rows" in prompt
        assert "SELECT COUNT(*) FROM t" in prompt

    def test_inference_prompt_has_empty_answer(self) -> None:
        prompt = build_prompt("CREATE TABLE t (id INT);", "Count rows")
        assert prompt.endswith("### SQL:\n")

    def test_strips_whitespace(self) -> None:
        prompt = build_prompt("  CREATE TABLE t (id INT);  ", "  Count rows  ")
        assert "  CREATE" not in prompt


class TestFormatExample:
    def test_returns_text_key(self) -> None:
        row = {
            "question": "How many rows?",
            "context": "CREATE TABLE t (id INT);",
            "answer": "SELECT COUNT(*) FROM t",
        }
        result = format_example(row)
        assert "text" in result
        assert isinstance(result["text"], str)

    def test_text_contains_answer(self) -> None:
        row = {
            "question": "How many rows?",
            "context": "CREATE TABLE t (id INT);",
            "answer": "SELECT COUNT(*) FROM t",
        }
        assert "SELECT COUNT(*) FROM t" in format_example(row)["text"]


class TestDatasetConfig:
    def test_defaults(self) -> None:
        cfg = DatasetConfig(dataset_id="b-mc2/sql-create-context")
        assert cfg.val_size == 0.05
        assert cfg.seed == 42
        assert cfg.max_samples is None

    @patch("data.dataset.load_dataset")
    def test_load_and_split_respects_max_samples(self, mock_load: MagicMock) -> None:
        from data.dataset import load_and_split

        mock_ds = MagicMock()
        mock_ds.select.return_value = mock_ds
        mock_ds.train_test_split.return_value = {"train": mock_ds, "test": mock_ds}
        mock_load.return_value = mock_ds

        cfg = DatasetConfig(dataset_id="b-mc2/sql-create-context", max_samples=500)
        load_and_split(cfg)
        mock_ds.select.assert_called_once_with(range(500))
