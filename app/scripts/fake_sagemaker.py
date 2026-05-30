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
    question: str = str(data.get("question", "")).lower()

    if "count" in question or "how many" in question:
        sql = "SELECT COUNT(*) FROM orders"
    elif "total" in question or "sum" in question:
        sql = "SELECT status, SUM(amount) FROM orders GROUP BY status"
    elif "expensive" in question or "most" in question:
        sql = "SELECT * FROM orders ORDER BY amount DESC LIMIT 5"
    elif "more than" in question or "having" in question:
        sql = "SELECT customer_id FROM orders GROUP BY customer_id HAVING COUNT(*) > 3"
    elif "join" in question or "name" in question:
        sql = (
            "SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id"
        )
    elif "above" in question or "average" in question:
        sql = "SELECT * FROM products WHERE price > (SELECT AVG(price) FROM products)"
    else:
        sql = "SELECT * FROM orders"

    return jsonify({"sql": sql})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
