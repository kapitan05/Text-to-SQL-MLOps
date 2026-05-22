#!/usr/bin/env python3
"""Merge LoRA adapter into base model weights and save as a HuggingFace checkpoint.

The merged checkpoint is then passed to convert_gguf.sh for GGUF quantization.

Usage:
    PYTHONPATH=. uv run python export/merge_and_export.py \\
        --base-model microsoft/Phi-3-mini-4k-instruct \\
        --adapter outputs/checkpoints/final_adapter \\
        --output-dir outputs/merged_model
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


def merge_and_save(
    base_model_id: str,
    adapter_path: str,
    output_dir: str,
    trust_remote_code: bool = True,
) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    logger.info("Loading base model in FP16 on CPU for clean merge ...")
    base = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        torch_dtype=torch.float16,
        device_map="cpu",
        trust_remote_code=trust_remote_code,
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model_id, trust_remote_code=trust_remote_code)

    logger.info("Loading LoRA adapter from %s ...", adapter_path)
    model = PeftModel.from_pretrained(base, adapter_path)

    logger.info("Merging adapter weights ...")
    model = model.merge_and_unload()

    logger.info("Saving merged model to %s ...", output_dir)
    model.save_pretrained(output_dir, safe_serialization=True)
    tokenizer.save_pretrained(output_dir)
    logger.info("Done. Pass %s to convert_gguf.sh.", output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--output-dir", default="outputs/merged_model")
    parser.add_argument("--no-trust-remote-code", action="store_false", dest="trust_remote_code")
    args = parser.parse_args()
    merge_and_save(args.base_model, args.adapter, args.output_dir, args.trust_remote_code)
