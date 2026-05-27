from __future__ import annotations

from datetime import datetime
from typing import Any

import boto3
from airflow import DAG
from airflow.operators.python import PythonOperator

from operators.dataset_formatter import DatasetFormatterOperator
from operators.s3_failed_sql_collector import S3FailedSQLCollectorOperator

FAILED_SQL_BUCKET = "text2sql-failed-sql"
DATASET_BUCKET = "text2sql-dataset"


def _upload(**context: Any) -> None:
    ti = context["ti"]
    jsonl: str = ti.xcom_pull(task_ids="format") or ""
    if not jsonl:
        return
    ds: str = context["ds"]
    key = "active_learning/{}/failed_sql.jsonl".format(ds.replace("-", "/"))
    boto3.client("s3").put_object(
        Bucket=DATASET_BUCKET,
        Key=key,
        Body=jsonl.encode(),
        ContentType="application/x-ndjson",
    )


with DAG(
    "active_learning",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["text2sql", "active-learning"],
) as dag:
    collect = S3FailedSQLCollectorOperator(
        task_id="collect",
        bucket=FAILED_SQL_BUCKET,
        ds="{{ ds }}",
    )

    format_task = DatasetFormatterOperator(
        task_id="format",
        collector_task_id="collect",
    )

    upload = PythonOperator(
        task_id="upload",
        python_callable=_upload,
    )

    collect >> format_task >> upload
