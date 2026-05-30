from __future__ import annotations

import os
from collections.abc import Generator
from typing import Any

import boto3
import pytest

_ENDPOINT = "http://localhost:4566"
_REGION = "us-east-1"
_TABLE = "query_results"
_BUCKET = "text2sql-failed-sql"


def _localstack_reachable() -> bool:
    import urllib.request

    try:
        urllib.request.urlopen(f"{_ENDPOINT}/_localstack/health", timeout=2)
        return True
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def localstack_env() -> Generator[None, None, None]:
    if not _localstack_reachable():
        pytest.skip(
            "LocalStack not reachable at http://localhost:4566"
            " — run: docker compose up localstack localstack-init -d"
        )

    # Set before any src.* import fires lru_cache
    os.environ.setdefault("AWS_ENDPOINT_URL", _ENDPOINT)
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    os.environ.setdefault("AWS_DEFAULT_REGION", _REGION)
    os.environ.setdefault("DYNAMODB_TABLE", _TABLE)
    os.environ.setdefault("FAILED_SQL_BUCKET", _BUCKET)
    os.environ.setdefault("SAGEMAKER_ENDPOINT_NAME", "text2sql-inference")

    # Evict any previously cached real-AWS connections
    from src.dynamo import _get_table
    from src.storage import _get_client

    _get_table.cache_clear()
    _get_client.cache_clear()

    yield


@pytest.fixture(scope="session")
def dynamodb_table(localstack_env: None) -> Any:
    resource = boto3.resource("dynamodb", endpoint_url=_ENDPOINT, region_name=_REGION)
    return resource.Table(_TABLE)


@pytest.fixture(scope="session")
def s3_client(localstack_env: None) -> Any:
    return boto3.client("s3", endpoint_url=_ENDPOINT, region_name=_REGION)
