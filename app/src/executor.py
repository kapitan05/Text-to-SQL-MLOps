from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


def create_db_from_ddl(ddl: str) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(ddl)
    except sqlite3.Error as exc:
        logger.debug("DDL warning (non-fatal): %s", exc)
    return conn


def execute_sql(conn: sqlite3.Connection, sql: str) -> list[dict[str, object]]:
    cursor = conn.execute(sql)
    cols = [desc[0] for desc in cursor.description or []]
    return [dict(zip(cols, tuple(row))) for row in cursor.fetchall()]
