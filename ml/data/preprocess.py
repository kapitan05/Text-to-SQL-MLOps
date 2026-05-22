"""Standalone preprocessing utilities for inspection and offline dataset building."""
from __future__ import annotations

import polars as pl
from datasets import Dataset

from modeling.prompts import build_prompt


def dataset_to_polars(ds: Dataset) -> pl.DataFrame:
    """Convert HuggingFace Dataset to Polars for offline exploration."""
    return pl.from_dicts(list(ds))


def compute_length_stats(df: pl.DataFrame, col: str = "text") -> dict[str, float]:
    """Return token-count proxy stats (char length / 4) for a text column."""
    lengths = df[col].str.len_chars() / 4
    return {
        "mean": float(lengths.mean() or 0),
        "p50": float(lengths.quantile(0.5) or 0),
        "p95": float(lengths.quantile(0.95) or 0),
        "max": float(lengths.max() or 0),
    }


def preview_prompt(context: str, question: str, answer: str = "") -> None:
    """Print a formatted prompt for manual inspection."""
    print(build_prompt(context, question, answer))
