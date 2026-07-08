from __future__ import annotations

from datetime import datetime

from operators.evidently_report import EvidentlyReportOperator

from airflow import DAG

with DAG(
    "daily_monitoring",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["text2sql", "monitoring"],
) as dag:
    EvidentlyReportOperator(
        task_id="evidently_report",
        ds="{{ ds }}",
    )
