from __future__ import annotations

import logging
import os
import threading
import time
from functools import lru_cache
from typing import Any

from flask import Flask, Response, jsonify, request
from llama_cpp import Llama
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    push_to_gateway,
)
from prompts import build_prompt

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

PUSHGATEWAY_URL = os.environ.get("PUSHGATEWAY_URL", "http://localhost:9091")
_PUSH_INTERVAL = int(os.environ.get("METRICS_PUSH_INTERVAL", "15"))

_GGUF_PATH = os.environ.get("GGUF_PATH", "/opt/ml/model/model_q4_k_m.gguf")
_N_CTX = int(os.environ.get("MODEL_N_CTX", "512"))
_N_THREADS = int(os.environ.get("MODEL_N_THREADS", "4"))

# ── Metrics (global registry — cumulative across all requests) ────────────────

_invocations_total = Counter(
    "text2sql_sagemaker_invocations_total",
    "SageMaker inference requests by outcome",
    ["status"],
)
_inference_duration = Histogram(
    "text2sql_sagemaker_inference_duration_seconds",
    "Time spent in llama-cpp model inference",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)
_model_load_seconds: Gauge = Gauge(
    "text2sql_sagemaker_model_load_seconds",
    "Time to load the GGUF model at startup",
)


def _push_loop() -> None:
    """Background daemon — pushes metrics to Pushgateway every
    METRICS_PUSH_INTERVAL seconds."""
    while True:
        time.sleep(_PUSH_INTERVAL)
        try:
            push_to_gateway(PUSHGATEWAY_URL, job="text2sql-sagemaker")
        except Exception:
            logger.warning("metrics push failed", exc_info=True)


threading.Thread(target=_push_loop, daemon=True, name="metrics-push").start()


@lru_cache(maxsize=1)
def _get_model() -> Llama:
    logger.info("Loading GGUF model from %s", _GGUF_PATH)
    t0 = time.monotonic()
    model = Llama(
        model_path=_GGUF_PATH,
        n_gpu_layers=-1,
        n_ctx=_N_CTX,
        n_threads=_N_THREADS,
        verbose=False,
    )
    load_time = time.monotonic() - t0
    logger.info("Model loaded in %.1fs", load_time)
    _model_load_seconds.set(load_time)
    return model


# Load model at startup so the first request isn't penalised
_get_model()


@app.get("/ping")
def ping() -> Response:
    return Response(status=200)


@app.get("/metrics")
def metrics() -> Response:
    """Prometheus /metrics endpoint — useful for local debugging."""
    return Response(generate_latest(), content_type="text/plain; version=0.0.4")


@app.post("/invocations")
def invocations() -> tuple[Response, int]:
    data: Any = request.get_json(force=True)
    question: str = data["question"]
    context: str = data["context"]

    prompt = build_prompt(context, question)
    t0 = time.monotonic()
    try:
        response: Any = _get_model()(
            prompt,
            max_tokens=64,
            temperature=0.0,
            stop=["###", "\n\n"],
        )
        elapsed = time.monotonic() - t0
        _inference_duration.observe(elapsed)
        _invocations_total.labels(status="success").inc()
        logger.info("Inference done in %.1fs for question: %.80s", elapsed, question)
        raw: str = str(response["choices"][0]["text"]).strip()
        sql = raw.split("\n")[0]
        return jsonify({"sql": sql}), 200
    except Exception:
        _invocations_total.labels(status="error").inc()
        logger.exception("Inference failed for question: %.80s", question)
        return jsonify({"error": "inference failed"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
