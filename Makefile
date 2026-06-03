.PHONY: lint format typecheck test test-int localstack-up localstack-down \
        airflow-up airflow-down build check monitoring-up monitoring-down evidently-report

lint:
	$(MAKE) -C app lint
	$(MAKE) -C ml lint

format:
	$(MAKE) -C app format
	$(MAKE) -C ml format

typecheck:
	$(MAKE) -C app typecheck
	$(MAKE) -C ml typecheck

test:
	$(MAKE) -C app test
	$(MAKE) -C ml test

test-int: localstack-up
	$(MAKE) -C app test-int

localstack-up:
	$(MAKE) -C app localstack-up

localstack-down:
	$(MAKE) -C app localstack-down

airflow-up:
	docker compose -f airflow/docker-compose.yml up -d

airflow-down:
	docker compose -f airflow/docker-compose.yml down

build:
	$(MAKE) -C app build

check: lint typecheck test

monitoring-up:
	docker compose -f monitoring/docker-compose.yml up -d

monitoring-down:
	docker compose -f monitoring/docker-compose.yml down

evidently-report:
	DYNAMODB_TABLE=query_results \
	FAILED_SQL_BUCKET=text2sql-failed-sql \
	MONITORING_BUCKET=text2sql-failed-sql \
	MLFLOW_TRACKING_URI=$$(cd infra && terraform output -raw monitoring_mlflow_url 2>/dev/null || echo "http://localhost:5000") \
	uv run --directory monitoring python evidently_report.py
