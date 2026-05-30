from __future__ import annotations

import logging
import os
import time
from functools import lru_cache
from typing import Any

from flask import Flask, Response, jsonify, request
from llama_cpp import Llama
from prompts import build_prompt

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

_GGUF_PATH = os.environ.get("GGUF_PATH", "/opt/ml/model/model_q4_k_m.gguf")
_N_CTX = int(os.environ.get("MODEL_N_CTX", "512"))
_N_THREADS = int(os.environ.get("MODEL_N_THREADS", "4"))


@lru_cache(maxsize=1)
def _get_model() -> Llama:
    logger.info("Loading GGUF model from %s", _GGUF_PATH)
    t0 = time.monotonic()
    model = Llama(
        model_path=_GGUF_PATH,
        n_gpu_layers=-1,  # offload all layers to GPU
        n_ctx=_N_CTX,
        n_threads=_N_THREADS,
        verbose=False,
    )
    logger.info("Model loaded in %.1fs", time.monotonic() - t0)
    return model


# Load model at startup so the first request isn't penalised
_get_model()


@app.get("/ping")
def ping() -> Response:
    return Response(status=200)


@app.post("/invocations")
def invocations() -> tuple[Response, int]:
    data: Any = request.get_json(force=True)
    question: str = data["question"]
    context: str = data["context"]

    prompt = build_prompt(context, question)
    t0 = time.monotonic()
    response: Any = _get_model()(
        prompt,
        max_tokens=64,
        temperature=0.0,
        stop=["###", "\n\n"],
    )
    elapsed = time.monotonic() - t0
    logger.info("Inference done in %.1fs for question: %.80s", elapsed, question)

    raw: str = str(response["choices"][0]["text"]).strip()
    sql = raw.split("\n")[0]

    return jsonify({"sql": sql}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
