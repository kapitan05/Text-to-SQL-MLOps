from __future__ import annotations

import sqlite3

import pytest

from src.executor import create_db_from_ddl, execute_sql

DDL = "CREATE TABLE orders (id INTEGER PRIMARY KEY, item TEXT, amount REAL);"
SEED = "INSERT INTO orders VALUES (1, 'apple', 1.50), (2, 'banana', 0.75);"


class TestCreateDbFromDdl:
    def test_executes_valid_ddl(self) -> None:
        conn = create_db_from_ddl(DDL + SEED)
        rows = conn.execute("SELECT COUNT(*) FROM orders").fetchone()
        assert rows[0] == 2

    def test_invalid_ddl_does_not_raise(self) -> None:
        conn = create_db_from_ddl("NOT VALID SQL;;;")
        assert isinstance(conn, sqlite3.Connection)

    def test_row_factory_set(self) -> None:
        conn = create_db_from_ddl(DDL + SEED)
        assert conn.row_factory is sqlite3.Row


class TestExecuteSql:
    def test_returns_list_of_dicts(self) -> None:
        conn = create_db_from_ddl(DDL + SEED)
        result = execute_sql(conn, "SELECT id, item FROM orders WHERE id = 1")
        assert result == [{"id": 1, "item": "apple"}]

    def test_empty_result_set(self) -> None:
        conn = create_db_from_ddl(DDL + SEED)
        result = execute_sql(conn, "SELECT * FROM orders WHERE amount > 100")
        assert result == []

    def test_multiple_rows(self) -> None:
        conn = create_db_from_ddl(DDL + SEED)
        result = execute_sql(conn, "SELECT id FROM orders ORDER BY id")
        assert [r["id"] for r in result] == [1, 2]

    def test_invalid_sql_raises(self) -> None:
        conn = create_db_from_ddl(DDL)
        with pytest.raises(sqlite3.Error):
            execute_sql(conn, "SELECT * FROM nonexistent_table")
