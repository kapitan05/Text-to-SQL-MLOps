#!/usr/bin/env python3
"""Pre-download dataset and base model weights to avoid timeouts during training.

Run before starting training on Vast.ai:
    PYTHONPATH=. uv run python data/download.py --model microsoft/Phi-3-mini-4k-instruct
"""
from __future__ import annotations

import argparse
import logging

from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


def main(model_id: str, trust_remote_code: bool = True) -> None:
    logger.info("Downloading dataset b-mc2/sql-create-context ...")
    ds = load_dataset("b-mc2/sql-create-context", split="train")
    logger.info("Dataset rows: %d", len(ds))

    logger.info("Downloading tokenizer for %s ...", model_id)
    AutoTokenizer.from_pretrained(model_id, trust_remote_code=trust_remote_code)

    logger.info("Downloading model weights (FP16, CPU) for %s ...", model_id)
    AutoModelForCausalLM.from_pretrained(
        model_id,
        trust_remote_code=trust_remote_code,
        low_cpu_mem_usage=True,
    )
    logger.info("All downloads complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="microsoft/Phi-3-mini-4k-instruct")
    parser.add_argument("--no-trust-remote-code", action="store_false", dest="trust_remote_code")
    args = parser.parse_args()
    main(args.model, args.trust_remote_code)
