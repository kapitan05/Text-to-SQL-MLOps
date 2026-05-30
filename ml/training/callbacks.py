from __future__ import annotations

import logging
from typing import Any

import mlflow
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainerCallback,
    TrainerControl,
    TrainerState,
    TrainingArguments,
)

from training.eval import compute_execution_accuracy

logger = logging.getLogger(__name__)


class MLflowExecutionAccuracyCallback(TrainerCallback):
    """Logs execution accuracy (EX) to MLflow at every eval checkpoint."""

    def __init__(
        self,
        val_examples: list[dict[str, Any]],
        tokenizer: AutoTokenizer,
        sample_size: int = 100,
        log_every_n_evals: int = 1,
    ) -> None:
        self.val_examples = val_examples
        self.tokenizer = tokenizer
        self.sample_size = sample_size
        self.log_every_n_evals = log_every_n_evals
        self._eval_count = 0

    def on_evaluate(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        model: AutoModelForCausalLM | None = None,
        **kwargs: object,
    ) -> None:
        self._eval_count += 1
        if self._eval_count % self.log_every_n_evals != 0:
            return
        ex = compute_execution_accuracy(
            model,
            self.tokenizer,
            self.val_examples,
            self.sample_size,
        )
        mlflow.log_metric("execution_accuracy", ex, step=state.global_step)
        logger.info("step=%d  execution_accuracy=%.4f", state.global_step, ex)
