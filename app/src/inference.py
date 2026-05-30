from __future__ import annotations

import json
import logging
import os
import time

import boto3
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

ENDPOINT_NAME = os.environ.get("SAGEMAKER_ENDPOINT_NAME", "text2sql-inference")

_RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)


@_RETRY
def generate_sql(question: str, context: str) -> str:
    client = boto3.client("sagemaker-runtime")
    payload = json.dumps({"question": question, "context": context})
    logger.info("Invoking SageMaker endpoint for question: %.80s", question)
    t0 = time.monotonic()
    resp = client.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType="application/json",
        Body=payload,
    )
    logger.info("SageMaker inference done in %.1fs", time.monotonic() - t0)
    return str(json.loads(resp["Body"].read())["sql"])
