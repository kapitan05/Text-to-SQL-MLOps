.PHONY: lint format typecheck test test-int localstack-up localstack-down \
        build lambda-up lambda-down check

lint:
	uv run ruff check . --fix

format:
	uv run ruff format .

typecheck:
	uv run mypy .

test:
	uv run pytest tests/ -v --ignore=tests/integration

test-int:
	uv run pytest tests/integration/ -v -m integration

localstack-up:
	docker compose up localstack localstack-init -d

localstack-down:
	docker compose stop localstack localstack-init

build:
	docker compose build lambda

lambda-up:
	docker compose up --build

lambda-down:
	docker compose down

check: lint typecheck test
