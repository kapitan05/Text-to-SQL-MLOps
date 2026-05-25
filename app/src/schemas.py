from __future__ import annotations

from pydantic import BaseModel


class QueryRequest(BaseModel):
    query_id: str
    question: str
    context: str  # DDL (CREATE TABLE statements)


class SQLResult(BaseModel):
    sql: str
    rows: list[dict[str, object]]
    latency_ms: float
    status: str = "success"


class FailedSQLLog(BaseModel):
    query_id: str
    question: str
    context: str
    error: str
    timestamp: str  # ISO-8601


class DynamoResultItem(BaseModel):
    query_id: str
    sql: str
    rows: str  # JSON-serialised list[dict] — avoids DynamoDB nested-type limits
    latency_ms: float
    status: str
    expires_at: int  # Unix epoch (TTL attribute)
