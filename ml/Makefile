.PHONY: lint format typecheck test download train train-docker export gguf mlflow-ui check

BASE_MODEL ?= microsoft/Phi-3-mini-4k-instruct
ADAPTER    ?= outputs/checkpoints/final_adapter
MERGED_DIR ?= outputs/merged_model
GGUF_OUT   ?= outputs/gguf

lint:
	uv run ruff check . --fix

format:
	uv run ruff format .

typecheck:
	uv run mypy .

test:
	uv run pytest tests/ -v

download:
	PYTHONPATH=. uv run python data/download.py --model microsoft/Phi-3-mini-4k-instruct

train:
	PYTHONPATH=. uv run python training/train.py \
		--model-config configs/model_config.yaml \
		--train-config configs/train_config.yaml \
		--mlflow-config configs/mlflow_config.yaml

train-docker:
	docker build -f Dockerfile.train -t text2sql-ml .
	docker run --gpus all --env-file ../.env \
		-v $(PWD)/outputs:/workspace/outputs \
		text2sql-ml

export:
	PYTHONPATH=. uv run python export/merge_and_export.py \
		--base-model $(BASE_MODEL) \
		--adapter $(ADAPTER) \
		--output-dir $(MERGED_DIR)

gguf:
	@test -n "$(MERGED_DIR)" || (echo "Usage: make gguf MERGED_DIR=<path> GGUF_OUT=<path>" && exit 1)
	bash export/convert_gguf.sh $(MERGED_DIR) $(GGUF_OUT)

mlflow-ui:
	uv run mlflow ui --backend-store-uri sqlite:///mlflow.db

check: lint typecheck test
