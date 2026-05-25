from __future__ import annotations

import base64
import json
import logging
from typing import Any

from src.schemas import QueryRequest

logger = logging.getLogger(__name__)


def decode_records(event: dict[str, Any]) -> list[QueryRequest]:
    requests: list[QueryRequest] = []
    for record in event.get("Records", []):
        raw = base64.b64decode(record["kinesis"]["data"]).decode()
        try:
            requests.append(QueryRequest.model_validate(json.loads(raw)))
        except Exception:
            logger.warning("Skipping malformed record: %.200s", raw)
    return requests
