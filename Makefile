.PHONY: lint format typecheck test test-int localstack-up localstack-down \
        airflow-up airflow-down build check

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
