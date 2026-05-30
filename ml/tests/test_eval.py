from __future__ import annotations

from unittest.mock import MagicMock, patch

from training.eval import _create_conn, _execute_safe, compute_execution_accuracy

DDL = "CREATE TABLE orders (id INTEGER PRIMARY KEY, amount REAL, status TEXT);"
SEED_SQL = "INSERT INTO orders VALUES (1, 99.9, 'paid'), (2, 49.5, 'pending');"


class TestCreateConn:
    def test_creates_in_memory_db(self) -> None:
        conn = _create_conn(DDL + SEED_SQL)
        rows = conn.execute("SELECT COUNT(*) FROM orders").fetchone()
        assert rows[0] == 2

    def test_invalid_ddl_does_not_raise(self) -> None:
        conn = _create_conn("NOT VALID SQL;;;")
        assert conn is not None


class TestExecuteSafe:
    def test_returns_row_set_on_success(self) -> None:
        conn = _create_conn(DDL + SEED_SQL)
        rows = _execute_safe(conn, "SELECT status FROM orders WHERE amount > 50")
        assert rows == {"('paid',)"}

    def test_returns_none_on_invalid_sql(self) -> None:
        conn = _create_conn(DDL)
        result = _execute_safe(conn, "SELECT * FROM nonexistent_table")
        assert result is None

    def test_empty_result_set(self) -> None:
        conn = _create_conn(DDL + SEED_SQL)
        rows = _execute_safe(conn, "SELECT * FROM orders WHERE amount > 1000")
        assert rows == set()


class TestExecutionAccuracy:
    def _make_example(self) -> dict[str, str]:
        return {
            "context": DDL + SEED_SQL,
            "question": "How many orders?",
            "answer": "SELECT COUNT(*) FROM orders",
        }

    @patch("training.eval._generate_sql", return_value="SELECT COUNT(*) FROM orders")
    def test_perfect_accuracy(self, _mock: MagicMock) -> None:
        examples = [self._make_example()] * 5
        acc = compute_execution_accuracy(
            MagicMock(), MagicMock(), examples, sample_size=5
        )
        assert acc == 1.0

    @patch("training.eval._generate_sql", return_value="SELECT * FROM nonexistent")
    def test_zero_accuracy_on_invalid_sql(self, _mock: MagicMock) -> None:
        examples = [self._make_example()] * 5
        acc = compute_execution_accuracy(
            MagicMock(), MagicMock(), examples, sample_size=5
        )
        assert acc == 0.0

    def test_empty_examples_returns_zero(self) -> None:
        acc = compute_execution_accuracy(MagicMock(), MagicMock(), [], sample_size=10)
        assert acc == 0.0

    @patch("training.eval._generate_sql", return_value="SELECT COUNT(*) FROM orders")
    def test_sample_size_limits_evaluation(self, mock_gen: MagicMock) -> None:
        examples = [self._make_example()] * 20
        compute_execution_accuracy(MagicMock(), MagicMock(), examples, sample_size=5)
        assert mock_gen.call_count == 5
