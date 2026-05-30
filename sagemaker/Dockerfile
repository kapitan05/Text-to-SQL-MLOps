# CPU-only SageMaker inference container for text2sql GGUF model
# Matches ml.m5.xlarge (no GPU). Build context: repo root.
FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y gcc g++ cmake && \
    rm -rf /var/lib/apt/lists/*

# CPU-only llama-cpp-python (no CMAKE_ARGS needed)
RUN pip install --no-cache-dir \
    "llama-cpp-python<0.3.0" \
    "flask>=3.0.0" \
    "pydantic>=2.8.0"

COPY models/model_q4_k_m.gguf /opt/ml/model/model_q4_k_m.gguf
COPY sagemaker/serve.py /serve.py
COPY sagemaker/prompts.py /prompts.py

ENV GGUF_PATH=/opt/ml/model/model_q4_k_m.gguf
ENV MODEL_N_CTX=512
ENV MODEL_N_THREADS=4

# SageMaker runs containers with "serve" as the command argument.
# This script puts "serve" in PATH so the container starts correctly.
RUN printf '#!/bin/sh\nexec python3 /serve.py\n' > /usr/local/bin/serve && \
    chmod +x /usr/local/bin/serve

EXPOSE 8080
CMD ["serve"]
