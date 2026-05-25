from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestGenerateSql:
    def _mock_model(self, text: str) -> MagicMock:
        model = MagicMock()
        model.return_value = {"choices": [{"text": text}]}
        return model

    def test_returns_first_line_of_output(self) -> None:
        from src.inference import generate_sql

        model = self._mock_model("SELECT COUNT(*) FROM t\nsome extra text")
        with patch("src.inference._get_model", return_value=model):
            result = generate_sql("How many rows?", "CREATE TABLE t (id INT);")

        assert result == "SELECT COUNT(*) FROM t"

    def test_strips_whitespace(self) -> None:
        from src.inference import generate_sql

        model = self._mock_model("  SELECT 1  ")
        with patch("src.inference._get_model", return_value=model):
            result = generate_sql("q", "CREATE TABLE t (id INT);")

        assert result == "SELECT 1"

    def test_prompt_contains_question_and_context(self) -> None:
        from src.inference import generate_sql

        model = self._mock_model("SELECT 1")
        with patch("src.inference._get_model", return_value=model):
            generate_sql("How many users?", "CREATE TABLE users (id INT);")

        call_args = model.call_args
        prompt: str = call_args.args[0]
        assert "How many users?" in prompt
        assert "CREATE TABLE users" in prompt

    def test_retries_on_failure_then_raises(self) -> None:
        from src.inference import generate_sql

        model = MagicMock()
        model.side_effect = RuntimeError("model error")
        with patch("src.inference._get_model", return_value=model):
            import pytest

            with pytest.raises(RuntimeError, match="model error"):
                generate_sql("q", "CREATE TABLE t (id INT);")

        assert model.call_count == 3
