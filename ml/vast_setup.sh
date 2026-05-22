#!/usr/bin/env bash
# One-time setup script for a fresh Vast.ai GPU instance.
#
# Prerequisites (set before running):
#   export AWS_ACCESS_KEY_ID=...
#   export AWS_SECRET_ACCESS_KEY=...
#   export AWS_DEFAULT_REGION=us-east-1
#   export MLFLOW_BUCKET=text2sql-mlflow-artifacts
#   export HF_TOKEN=...   # only required for gated models (Llama-3)
#
# Usage:
#   git clone <repo> /workspace/SmartSearch
#   cd /workspace/SmartSearch/ml
#   bash vast_setup.sh
set -euo pipefail

echo "==> Installing system dependencies ..."
apt-get update -q && apt-get install -y -q git cmake build-essential curl

echo "==> Installing uv ..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

echo "==> Syncing Python dependencies ..."
cd /workspace/SmartSearch/ml
uv sync --frozen

echo "==> Verifying GPU ..."
uv run python -c "import torch; assert torch.cuda.is_available(), 'No CUDA GPU found'; print('GPU:', torch.cuda.get_device_name(0))"

echo "==> Starting MLflow tracking server (background) ..."
nohup uv run mlflow server \
    --backend-store-uri sqlite:///mlflow.db \
    --artifacts-destination "s3://${MLFLOW_BUCKET}/artifacts" \
    --host 0.0.0.0 \
    --port 5000 \
    --serve-artifacts \
    > mlflow_server.log 2>&1 &
MLFLOW_PID=$!
echo "   MLflow PID=$MLFLOW_PID | http://$(curl -s ifconfig.me 2>/dev/null || echo '<vast-ip>'):5000"
echo "   Logs: tail -f /workspace/SmartSearch/ml/mlflow_server.log"

echo ""
echo "==> Setup complete. Run training with:"
echo "   cd /workspace/SmartSearch/ml"
echo "   PYTHONPATH=. uv run python training/train.py"
