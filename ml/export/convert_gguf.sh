#!/usr/bin/env bash
# Convert a merged HuggingFace checkpoint to GGUF Q4_K_M.
#
# Usage:
#   bash export/convert_gguf.sh <merged_model_dir> <output_dir>
#
# Output:
#   <output_dir>/model_fp16.gguf   (intermediate, ~7GB for Phi-3-mini)
#   <output_dir>/model_q4_k_m.gguf (final, ~2.2GB for Phi-3-mini)
set -euo pipefail

MERGED_DIR="${1:?Usage: $0 <merged_model_dir> <output_dir>}"
OUTPUT_DIR="${2:?Usage: $0 <merged_model_dir> <output_dir>}"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-./llama.cpp}"

mkdir -p "$OUTPUT_DIR"

if [ ! -d "$LLAMA_CPP_DIR" ]; then
    echo "Cloning llama.cpp ..."
    git clone --depth 1 https://github.com/ggerganov/llama.cpp "$LLAMA_CPP_DIR"
fi

if [ ! -f "$LLAMA_CPP_DIR/build/bin/llama-quantize" ]; then
    echo "Building llama.cpp ..."
    cmake -B "$LLAMA_CPP_DIR/build" -S "$LLAMA_CPP_DIR" -DCMAKE_BUILD_TYPE=Release
    cmake --build "$LLAMA_CPP_DIR/build" --config Release -j "$(nproc)"
fi

echo "Step 1/2: Converting HF checkpoint → FP16 GGUF ..."
uv run python "$LLAMA_CPP_DIR/convert_hf_to_gguf.py" \
    "$MERGED_DIR" \
    --outtype f16 \
    --outfile "$OUTPUT_DIR/model_fp16.gguf"

echo "Step 2/2: Quantizing FP16 GGUF → Q4_K_M ..."
"$LLAMA_CPP_DIR/build/bin/llama-quantize" \
    "$OUTPUT_DIR/model_fp16.gguf" \
    "$OUTPUT_DIR/model_q4_k_m.gguf" \
    Q4_K_M

echo "Done."
echo "  FP16:  $(du -sh "$OUTPUT_DIR/model_fp16.gguf" | cut -f1)   $OUTPUT_DIR/model_fp16.gguf"
echo "  Q4_KM: $(du -sh "$OUTPUT_DIR/model_q4_k_m.gguf" | cut -f1)   $OUTPUT_DIR/model_q4_k_m.gguf"
