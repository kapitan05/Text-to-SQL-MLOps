#!/usr/bin/env python3
"""Main training entrypoint.

Usage (from ml/ directory):
    PYTHONPATH=. uv run python training/train.py
    PYTHONPATH=. uv run python training/train.py \
        --model-config configs/model_config.yaml
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import cast

import mlflow
import yaml
from pydantic import BaseModel
from trl import SFTConfig, SFTTrainer

from data.dataset import DatasetConfig, apply_formatting, load_and_split
from modeling.model import LoRAAdapterConfig, QLoRAConfig, apply_lora, load_base_model
from training.callbacks import MLflowExecutionAccuracyCallback

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class MLflowCfg(BaseModel):
    tracking_uri: str
    experiment_name: str
    artifact_bucket: str
    run_tags: dict[str, str] = {}


class FullConfig(BaseModel):
    model_id: str
    trust_remote_code: bool = True
    max_seq_length: int = 1024
    qlora: QLoRAConfig
    lora: LoRAAdapterConfig
    dataset: DatasetConfig
    sft: dict[str, object]
    mlflow: MLflowCfg


def _read_yaml(path: str) -> dict[str, object]:
    return cast(dict[str, object], yaml.safe_load(Path(path).read_text()))


def load_config(model_cfg: str, train_cfg: str, mlflow_cfg: str) -> FullConfig:
    mc = _read_yaml(model_cfg)
    tc = _read_yaml(train_cfg)
    mf = _read_yaml(mlflow_cfg)

    dataset_keys = {"dataset_id", "dataset_split", "val_size", "seed", "max_samples"}
    sft_keys = {k for k in tc if k not in dataset_keys}

    return FullConfig(
        model_id=mc["base_model_id"],  # type: ignore[arg-type]
        trust_remote_code=mc.get("trust_remote_code", True),  # type: ignore[arg-type]
        max_seq_length=mc.get("max_seq_length", 1024),  # type: ignore[arg-type]
        qlora=QLoRAConfig(**mc["qlora"]),  # type: ignore[arg-type]
        lora=LoRAAdapterConfig(**mc["lora"]),  # type: ignore[arg-type]
        dataset=DatasetConfig(**{k: tc[k] for k in dataset_keys if k in tc}),  # type: ignore[arg-type]
        sft={k: tc[k] for k in sft_keys},
        mlflow=MLflowCfg(**mf),  # type: ignore[arg-type]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-config", default="configs/model_config.yaml")
    parser.add_argument("--train-config", default="configs/train_config.yaml")
    parser.add_argument("--mlflow-config", default="configs/mlflow_config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.model_config, args.train_config, args.mlflow_config)

    mlflow.set_tracking_uri(cfg.mlflow.tracking_uri)
    os.environ.setdefault("MLFLOW_S3_ENDPOINT_URL", "https://s3.amazonaws.com")
    mlflow.set_experiment(cfg.mlflow.experiment_name)

    dataset_dict = load_and_split(cfg.dataset)
    formatted = apply_formatting(dataset_dict)
    val_raw = list(dataset_dict["validation"])

    model, tokenizer = load_base_model(cfg.model_id, cfg.qlora, cfg.trust_remote_code)
    model = apply_lora(model, cfg.lora)
    model.print_trainable_parameters()

    # max_seq_length was removed from SFTConfig in TRL >=0.15; set on tokenizer instead
    tokenizer.model_max_length = cfg.max_seq_length

    sft_config = SFTConfig(
        dataset_text_field="text",
        **cfg.sft,
    )

    ex_callback = MLflowExecutionAccuracyCallback(
        val_examples=val_raw,
        tokenizer=tokenizer,
        sample_size=100,
    )

    with mlflow.start_run(tags=cfg.mlflow.run_tags) as run:
        mlflow.log_params(
            {
                "base_model": cfg.model_id,
                "lora_r": cfg.lora.r,
                "lora_alpha": cfg.lora.lora_alpha,
                "learning_rate": cfg.sft.get("learning_rate"),
                "num_train_epochs": cfg.sft.get("num_train_epochs"),
                "dataset": cfg.dataset.dataset_id,
            }
        )
        logger.info("MLflow run_id: %s", run.info.run_id)

        trainer = SFTTrainer(
            model=model,
            train_dataset=formatted["train"],
            eval_dataset=formatted["validation"],
            processing_class=tokenizer,
            args=sft_config,
            callbacks=[ex_callback],
        )
        trainer.train()

        adapter_path = Path(cfg.sft.get("output_dir", "./outputs")) / "final_adapter"  # type: ignore[arg-type]
        model.save_pretrained(str(adapter_path))
        tokenizer.save_pretrained(str(adapter_path))
        mlflow.log_artifacts(str(adapter_path), artifact_path="adapter")
        logger.info("Adapter saved → %s and logged to MLflow.", adapter_path)


if __name__ == "__main__":
    main()
