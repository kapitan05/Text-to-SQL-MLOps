from __future__ import annotations

import logging
import sqlite3
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from modeling.prompts import build_prompt

logger = logging.getLogger(__name__)


def _create_conn(schema_ddl: str) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(schema_ddl)
    except sqlite3.Error as exc:
        logger.debug("DDL warning (non-fatal): %s", exc)
    return conn


def _execute_safe(conn: sqlite3.Connection, sql: str) -> set[str] | None:
    try:
        cursor = conn.execute(sql)
        return {str(row) for row in cursor.fetchall()}
    except sqlite3.Error:
        return None


def _generate_sql(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    context: str,
    question: str,
    max_new_tokens: int = 128,
) -> str:
    prompt = build_prompt(context, question)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip().split("\n")[0]


def compute_execution_accuracy(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    examples: list[dict[str, Any]],
    sample_size: int = 100,
) -> float:
    """EX metric: fraction of generated SQLs that return the same rows as the gold SQL."""
    sample = examples[:sample_size]
    if not sample:
        return 0.0
    correct = 0
    for ex in sample:
        pred_sql = _generate_sql(model, tokenizer, ex["context"], ex["question"])
        conn = _create_conn(ex["context"])
        pred_rows = _execute_safe(conn, pred_sql)
        gold_rows = _execute_safe(conn, ex["answer"])
        conn.close()
        if pred_rows is not None and pred_rows == gold_rows:
            correct += 1
    return correct / len(sample)
