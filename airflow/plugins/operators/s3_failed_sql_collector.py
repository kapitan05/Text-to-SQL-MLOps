from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from airflow.models import BaseOperator

logger = logging.getLogger(__name__)


class S3FailedSQLCollectorOperator(BaseOperator):
    template_fields = ("ds",)

    def __init__(self, *, bucket: str, ds: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.bucket = bucket
        self.ds = ds

    def execute(self, context: Any) -> list[dict[str, Any]]:
        prefix = "failed_sql/{}/".format(self.ds.replace("-", "/"))
        client = boto3.client("s3")
        paginator = client.get_paginator("list_objects_v2")
        records: list[dict[str, Any]] = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                body = client.get_object(Bucket=self.bucket, Key=obj["Key"])["Body"].read()
                records.append(json.loads(body))
        logger.info("Collected %d failed SQL records for %s", len(records), self.ds)
        return records
