from __future__ import annotations

import json
import logging
import os
import time

import boto3
from tenacity import RetryCallState, retry, stop_after_attempt, wait_exponential

from src import metrics

logger = logging.getLogger(__name__)

ENDPOINT_NAME = os.environ.get("SAGEMAKER_ENDPOINT_NAME", "text2sql-inference")
_RUNTIME_ENDPOINT = os.environ.get("SAGEMAKER_RUNTIME_ENDPOINT_URL") or None


def _count_retry(retry_state: RetryCallState) -> None:
    """before_sleep callback — fires after a failed attempt, before the next sleep."""
    try:
        metrics.current().inference_retries.labels(
            attempt=str(retry_state.attempt_number)
        ).inc()
    except Exception:
        pass


_RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
    before_sleep=_count_retry,
)


@_RETRY
def generate_sql(question: str, context: str) -> str:
    client = boto3.client("sagemaker-runtime", endpoint_url=_RUNTIME_ENDPOINT)
    payload = json.dumps({"question": question, "context": context})
    logger.info("Invoking SageMaker endpoint for question: %.80s", question)
    t0 = time.monotonic()
    resp = client.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType="application/json",
        Body=payload,
    )
    duration = time.monotonic() - t0
    logger.info("SageMaker inference done in %.1fs", duration)
    try:
        metrics.current().inference_duration.observe(duration)
    except Exception:
        pass
    return str(json.loads(resp["Body"].read())["sql"])
