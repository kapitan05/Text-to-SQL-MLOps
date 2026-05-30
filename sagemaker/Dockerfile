# GPU SageMaker inference container for text2sql GGUF model
# Matches ml.g4dn.xlarge (CUDA 11.8). Build context: repo root.
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y python3 python3-pip gcc g++ cmake && \
    rm -rf /var/lib/apt/lists/*

# CUDA-enabled llama-cpp-python
RUN CMAKE_ARGS="-DGGML_CUDA=on" pip3 install --no-cache-dir \
    "llama-cpp-python<0.3.0" \
    "flask>=3.0.0" \
    "pydantic>=2.8.0" \
    "prometheus-client>=0.19.0"

COPY models/model_q4_k_m.gguf /opt/ml/model/model_q4_k_m.gguf
COPY sagemaker/serve.py /serve.py
COPY sagemaker/prompts.py /prompts.py

ENV GGUF_PATH=/opt/ml/model/model_q4_k_m.gguf
ENV MODEL_N_CTX=512
ENV MODEL_N_THREADS=4

# SageMaker runs containers with "serve" as the command argument.
# NVIDIA base image has its own ENTRYPOINT that tries exec serve → must be in PATH.
RUN printf '#!/bin/sh\nexec python3 /serve.py\n' > /usr/local/bin/serve && \
    chmod +x /usr/local/bin/serve

EXPOSE 8080
CMD ["serve"]
