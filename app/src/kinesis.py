from __future__ import annotations

import base64
import json
import logging
from typing import Any

from src import metrics
from src.schemas import QueryRequest

logger = logging.getLogger(__name__)


def decode_records(event: dict[str, Any]) -> list[QueryRequest]:
    requests: list[QueryRequest] = []
    for record in event.get("Records", []):
        raw = base64.b64decode(record["kinesis"]["data"]).decode()
        try:
            requests.append(QueryRequest.model_validate(json.loads(raw)))
            try:
                metrics.current().kinesis_records.labels(status="valid").inc()
            except Exception:
                pass
        except Exception:
            logger.warning("Skipping malformed record: %.200s", raw)
            try:
                metrics.current().kinesis_records.labels(status="malformed").inc()
            except Exception:
                pass
    return requests
