# GPU SageMaker inference container for text2sql GGUF model
# Targets ml.g4dn.xlarge (T4, CUDA 11.8). Build context: repo root.
# Build: docker buildx build --platform linux/amd64 -t text2sql-sagemaker .
FROM nvidia/cuda:11.8.0-runtime-ubuntu20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Pre-built cu118 wheel — no CUDA compilation; buildable on M1 via buildx.
# Kept as a separate layer so rebuilds don't re-download this ~100 MB wheel.
RUN pip3 install --no-cache-dir \
    "llama-cpp-python<0.3.0" \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu118
RUN python3 -c "from llama_cpp import Llama"

RUN pip3 install --no-cache-dir \
    "flask>=3.0.0" \
    "pydantic>=2.8.0" \
    "prometheus-client>=0.19.0"

COPY models/model_q4_k_m.gguf /opt/ml/model/model_q4_k_m.gguf
COPY sagemaker/serve.py /serve.py
COPY sagemaker/prompts.py /prompts.py

ENV GGUF_PATH=/opt/ml/model/model_q4_k_m.gguf
ENV MODEL_N_CTX=512
ENV MODEL_N_THREADS=4

RUN printf '#!/bin/sh\nexec python3 /serve.py\n' > /usr/local/bin/serve && \
    chmod +x /usr/local/bin/serve

EXPOSE 8080
CMD ["/usr/local/bin/serve"]
