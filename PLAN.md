# Text2SQL Streaming Pipeline — Implementation Plan

## Context

Production-grade Text2SQL system for portfolio. Fine-tune an LLM on SQL generation, serve it via CPU inference in Lambda triggered by Kinesis, and close the feedback loop daily via Airflow collecting failed queries from S3 into an active-learning dataset. Note: SmartSearch repo repurposed — was empty.

---

## Architecture

```
Client
  └─ POST /query ──► API Gateway ──► Kinesis PutRecord  (async; returns 200 Accepted immediately)
                                          │
                              Lambda (Kinesis trigger, batch)
                                          │
                          llama-cpp-python  (GGUF, CPU-only)
                                          │
                     ┌────────────────────┴──────────────────────────┐
                     │ success → DynamoDB (PK: query_id)             │
                     │           {sql, rows, latency_ms, status}     │
                     │                                               │
                     │ failure  → S3  failed_sql/YYYY/MM/DD/         │
                     └───────────────────────────────────────────────┘

Client (poll)
  └─ GET /query/{query_id} ──► (future endpoint) reads DynamoDB result

Vast.ai (QLoRA train)
  └─ MLflow (SQLite backend + S3 artifact store)
       └─ GGUF export → baked into Lambda ECR image

Airflow (daily DAG)
  └─ S3 failed SQL → formatted JSONL → S3 dataset bucket
```

> **Async contract:** the POST /query endpoint acknowledges receipt only. Callers retrieve results by polling GET /query/{query_id} (not provisioned in Phase 3 — noted as follow-on work).

---

## Directory Tree

### `ml/`

```
ml/
├── configs/
│   ├── model_config.yaml      # base model ID, QLoRA params, LoRA params
│   ├── train_config.yaml      # dataset, batch size, LR, epochs, eval steps
│   └── mlflow_config.yaml     # tracking URI, experiment name, S3 bucket
├── data/
│   ├── download.py            # pre-fetch dataset + model weights (Vast.ai)
│   ├── preprocess.py          # raw rows → formatted prompt strings
│   └── dataset.py             # Pydantic schemas; load + split + map
├── modeling/
│   ├── model.py               # BnB 4-bit config, load base model, apply LoRA
│   └── prompts.py             # all prompt templates (isolated from logic)
├── training/
│   ├── train.py               # entrypoint: load configs, SFTTrainer, MLflow run
│   ├── callbacks.py           # MLflowExecutionAccuracyCallback (log EX @ eval)
│   └── eval.py                # compute_execution_accuracy: gen SQL → SQLite → compare
├── export/
│   ├── merge_and_export.py    # load FP16 base + LoRA → merge_and_unload → save HF
│   └── convert_gguf.sh        # clone llama.cpp → convert_hf_to_gguf.py → quantize Q4_K_M
├── tests/
│   ├── test_dataset.py
│   └── test_eval.py
├── Dockerfile.train           # nvcr.io/nvidia/pytorch:24.05-py3 base
├── vast_setup.sh              # install uv, sync deps, start MLflow server, print URL
└── pyproject.toml
```

### `app/`

```
app/
├── src/
│   ├── schemas.py        # Pydantic: QueryRequest, SQLResult, FailedSQLLog, DynamoResultItem
│   ├── kinesis.py        # decode base64 Kinesis records → list[QueryRequest] (query_id required)
│   ├── inference.py      # module-level Llama() init; generate_sql with tenacity retry
│   ├── executor.py       # create_db_from_ddl (in-memory SQLite); execute_sql
│   ├── dynamo.py         # write SQLResult to DynamoDB (PK: query_id); tenacity retry
│   ├── storage.py        # boto3 S3 put_object for FailedSQLLog; tenacity retry
│   └── handler.py        # parse → generate → execute → DynamoDB (success) / S3 (failure)
├── tests/
│   ├── test_executor.py
│   ├── test_handler.py   # mock generate_sql, dynamo.write_result, storage.log_failed_sql
│   ├── test_inference.py
│   └── test_dynamo.py    # mock boto3 resource; assert correct PK + item shape
├── Dockerfile
├── docker-compose.yml    # LocalStack (S3 + Kinesis + DynamoDB) + Lambda RIE
└── pyproject.toml
```

### `infra/`

```
infra/
├── modules/
│   ├── s3/                    # failed-sql bucket, MLflow-artifacts bucket, dataset bucket
│   ├── kinesis/               # stream (shard_count=1), CloudWatch iterator-age alarm
│   ├── lambda/                # container image function, IAM role, Kinesis trigger, concurrency cap
│   ├── api_gateway/           # REST API, POST /query, direct Kinesis PutRecord integration
│   └── dynamodb/              # table: query_results (PK: query_id, TTL: expires_at)
├── main.tf
├── variables.tf
├── outputs.tf
├── provider.tf
└── terraform.tfvars.example
```

### `airflow/`

```
airflow/
├── dags/active_learning_dag.py
├── plugins/operators/
│   ├── s3_failed_sql_collector.py
│   └── dataset_formatter.py
├── docker-compose.yml
└── requirements.txt
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Base model | `microsoft/Phi-3-mini-4k-instruct` (3.8B) | Q4_K_M ~2.2GB → fits Lambda 8GB RAM; faster CPU inference than 8B |
| QLoRA | NF4, double quant, bfloat16 compute | Standard for 4-bit SFT; best memory/quality tradeoff |
| LoRA targets | all linear projections (q/k/v/o + gate/up/down) | SQL generation benefits from full attention + FFN tuning |
| LoRA rank | r=64, alpha=128 | Higher rank justified for code/SQL domain shift |
| Dataset split | 95% train / 5% val (~3.9k) | Enough for EX metric evaluation during training |
| EX metric | Run predicted + gold SQL against in-memory SQLite; compare row sets | Standard Text2SQL evaluation; directly measures task success |
| MLflow backend | SQLite on Vast.ai + S3 artifact store | No infra needed for tracking server; artifacts persist after instance teardown |
| GGUF quantization | Q4_K_M | Best quality-size tradeoff for 4-bit; ~4× compression vs FP16 |
| Lambda model loading | Module-level `Llama()` init (outside handler) | Cached across warm invocations; avoids re-loading ~2GB per request |
| Lambda container | Bake GGUF into `/opt` in ECR image | Eliminates runtime download; cold start is init-only |
| Lambda concurrency | Reserved cap = 5 | Cost guard for portfolio project |
| API GW → Kinesis | Direct AWS service integration | No Lambda hop on ingest path; Kinesis decouples rate |
| Result store | DynamoDB, PK = `query_id`, TTL = 24h | Async pipeline needs a side-channel for results; DynamoDB gives single-digit ms reads |
| Failure routing | S3 only (not DynamoDB) | Failed SQL needs to be queryable by Airflow as a dataset, not retrieved by clients |
| DynamoDB item TTL | 24 hours | Results are ephemeral; TTL avoids unbounded table growth |

---

## Implementation Phases

### Phase 1 — ML Pipeline

1. Scaffold `ml/` with `pyproject.toml` (torch, transformers, peft, bitsandbytes, trl, datasets, mlflow, pydantic, polars, tenacity)
2. Write `prompts.py` first — all other modules depend on the prompt format
3. Implement `dataset.py`: `SQLExample` Pydantic model, `load_and_split`, `format_example`
4. Implement `model.py`: `QLoRAConfig` + `LoRAAdapterConfig` Pydantic models, `load_base_model`, `apply_lora`
5. Implement `eval.py`: `compute_execution_accuracy` — generates SQL via greedy decode, runs both gold + pred against SQLite, returns fraction matching
6. Implement `callbacks.py`: `MLflowExecutionAccuracyCallback` — calls eval on a 100-sample subset at each eval step
7. Implement `train.py`: reads all three YAMLs → `SFTTrainer` with the callback → `mlflow.start_run` wraps everything → saves adapter as MLflow artifact
8. Write `merge_and_export.py`: loads base in FP16 (CPU), `PeftModel.from_pretrained` + `merge_and_unload`, saves to HF format
9. Write `convert_gguf.sh`: clone llama.cpp → `convert_hf_to_gguf.py --outtype f16` → `llama-quantize Q4_K_M`
10. Write `vast_setup.sh`: install uv, sync deps, start MLflow server with `--artifacts-destination s3://...`
11. Write tests; run `uv run pytest`, `ruff`, `mypy`

### Phase 2 — Inference App

1. Scaffold `app/` with `pyproject.toml` (llama-cpp-python, pydantic, boto3, tenacity)
2. Implement `schemas.py`: `QueryRequest` (query_id required), `SQLResult`, `FailedSQLLog`, `DynamoResultItem`
3. Implement `kinesis.py`: decode base64 Kinesis records → `list[QueryRequest]`; validate query_id present
4. Implement `executor.py`: `create_db_from_ddl` (in-memory SQLite), `execute_sql` → `list[dict]`
5. Implement `inference.py`: module-level `Llama()` init via `lru_cache`, `generate_sql` with tenacity retry
6. Implement `dynamo.py`: `write_result(item: DynamoResultItem)` — puts item with query_id PK + TTL; tenacity retry
7. Implement `storage.py`: S3 `put_object` for `FailedSQLLog` with date-partitioned key, tenacity retry
8. Implement `handler.py`: success path → `dynamo.write_result`; failure path → `storage.log_failed_sql`
9. Write tests (executor: no mocks; handler/dynamo: mock boto3)
10. Write two-stage `Dockerfile`: builder stage compiles llama-cpp-python; final stage is clean Lambda image with GGUF in `/opt`
11. Write `docker-compose.yml` with LocalStack (S3 + Kinesis + DynamoDB) + Lambda RIE

### Phase 3 — Infrastructure

1. Write `modules/s3`: failed-sql bucket, MLflow-artifacts bucket, dataset bucket
2. Write `modules/kinesis`: stream (shard_count=1), CloudWatch iterator-age alarm
3. Write `modules/dynamodb`: `query_results` table, PK=`query_id` (String), TTL attribute=`expires_at`; on-demand billing
4. Write `modules/lambda`: container image function (8192 MB, 300s timeout, concurrency=5), IAM role (Kinesis read + S3 write + DynamoDB PutItem), Kinesis event source mapping
5. Write `modules/api_gateway`: REST API, `POST /query`, direct Kinesis `PutRecord` integration with request mapping template (base64 body + requestId partition key)
6. Wire modules in `main.tf`; add `provider.tf` with S3 remote state backend
7. `terraform validate` + `terraform plan`

### Phase 4 — Airflow

1. Write `s3_failed_sql_collector.py`: lists `failed_sql/{{ ds }}/` partition, downloads each JSON
2. Write `dataset_formatter.py`: parses `FailedSQLLog` → `{question, context, answer: ""}` JSONL (answer empty — for human labeling or re-inference)
3. Write `active_learning_dag.py`: `@daily`, `collect >> format >> upload`, `catchup=False`
4. Stand up with `docker compose up airflow-init && docker compose up`

---

## Verification

| Phase | Command |
|---|---|
| 1 — unit tests | `cd ml && uv run pytest tests/ -v` |
| 1 — lint/types | `uv run ruff check . --fix && uv run ruff format . && uv run mypy .` |
| 1 — data dry-run | `uv run python data/download.py --model microsoft/Phi-3-mini-4k-instruct` |
| 1 — train (Vast.ai) | `bash vast_setup.sh && uv run python training/train.py` |
| 1 — GGUF export | `uv run python export/merge_and_export.py ... && bash export/convert_gguf.sh ...` |
| 2 — unit tests | `cd app && uv run pytest tests/ -v --cov=src` |
| 2 — local Lambda | `docker compose up --build` then invoke via Lambda RIE endpoint |
| 3 — infra | `cd infra && terraform init && terraform validate && terraform plan` |
| 4 — Airflow | DAG visible + triggerable at `http://localhost:8080` |
