from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from tenacity import retry, stop_after_attempt, wait_exponential

from src.prompts import build_prompt

if TYPE_CHECKING:
    from llama_cpp import Llama

logger = logging.getLogger(__name__)

GGUF_PATH = os.environ.get("GGUF_PATH", "/opt/model.gguf")
_N_CTX = int(os.environ.get("MODEL_N_CTX", "1024"))
_N_THREADS = int(os.environ.get("MODEL_N_THREADS", "4"))


@lru_cache(maxsize=1)
def _get_model() -> Llama:
    from llama_cpp import Llama  # lazy — avoids import cost when mocked in tests

    logger.info("Loading GGUF model from %s", GGUF_PATH)
    return Llama(
        model_path=GGUF_PATH,
        n_ctx=_N_CTX,
        n_threads=_N_THREADS,
        verbose=False,
    )


_RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)


@_RETRY
def generate_sql(question: str, context: str) -> str:
    model = _get_model()
    prompt = build_prompt(context, question)
    response: Any = model(
        prompt,
        max_tokens=64,
        temperature=0.0,
        stop=["###", "\n\n"],
    )
    raw: str = str(response["choices"][0]["text"]).strip()
    return raw.split("\n")[0]
