from __future__ import annotations

from datasets import DatasetDict, load_dataset
from pydantic import BaseModel

from modeling.prompts import build_prompt


class SQLExample(BaseModel):
    question: str
    context: str  # DDL (CREATE TABLE statements)
    answer: str  # gold SQL


class DatasetConfig(BaseModel):
    dataset_id: str
    dataset_split: str = "train"
    val_size: float = 0.05
    seed: int = 42
    max_samples: int | None = None


def load_and_split(cfg: DatasetConfig) -> DatasetDict:
    ds = load_dataset(cfg.dataset_id, split=cfg.dataset_split)
    if cfg.max_samples:
        ds = ds.select(range(cfg.max_samples))
    split = ds.train_test_split(test_size=cfg.val_size, seed=cfg.seed)
    return DatasetDict({"train": split["train"], "validation": split["test"]})


def format_example(row: dict[str, str]) -> dict[str, str]:
    example = SQLExample(
        question=row["question"],
        context=row["context"],
        answer=row["answer"],
    )
    return {"text": build_prompt(example.context, example.question, example.answer)}


def apply_formatting(dataset_dict: DatasetDict) -> DatasetDict:
    return dataset_dict.map(
        format_example,
        remove_columns=["question", "context", "answer"],
    )
