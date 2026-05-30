"""
Fake SageMaker endpoint for local development and docker-compose testing.

Implements the SageMaker container contract:
  GET  /ping        → 200 OK  (health check)
  POST /invocations → {"sql": "..."} (fixed mock response, no GGUF model)

Usage:
  python scripts/fake_sagemaker.py          # direct
  docker compose up fake-sagemaker          # via docker-compose
"""

from __future__ import annotations

from flask import Flask, Response, jsonify, request

app = Flask(__name__)


@app.get("/ping")  # type: ignore[untyped-decorator]
def ping() -> Response:
    return Response(status=200)


@app.post("/invocations")  # type: ignore[untyped-decorator]
def invocations() -> Response:
    data = request.get_json(force=True)
    context: str = str(data.get("context", ""))

    # Extract first table name from DDL so the SQL is always valid for the given schema.
    # Purpose: verify infrastructure pipeline, not SQL correctness.
    import re

    match = re.search(r"CREATE\s+TABLE\s+(\w+)", context, re.IGNORECASE)
    table = match.group(1) if match else "t"
    sql = f"SELECT * FROM {table} LIMIT 1"

    return jsonify({"sql": sql})


@app.post("/endpoints/<string:name>/invocations")  # type: ignore[untyped-decorator]
def endpoint_invocations(name: str) -> Response:
    return invocations()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
