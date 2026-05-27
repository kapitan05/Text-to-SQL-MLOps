from __future__ import annotations

import json
import logging
from typing import Any

from airflow.models import BaseOperator

logger = logging.getLogger(__name__)


class DatasetFormatterOperator(BaseOperator):
    def __init__(self, *, collector_task_id: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.collector_task_id = collector_task_id

    def execute(self, context: Any) -> str:
        records: list[dict[str, Any]] = (
            context["ti"].xcom_pull(task_ids=self.collector_task_id) or []
        )
        lines = [
            json.dumps({"question": r["question"], "context": r["context"], "answer": ""})
            for r in records
        ]
        logger.info("Formatted %d records into JSONL", len(lines))
        return "\n".join(lines)
