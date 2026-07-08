# GPU SageMaker inference container for text2sql GGUF model
# Targets ml.g4dn.xlarge (T4, CUDA 11.8, compute capability 7.5).
# Build context: repo root. Two-stage: CUDA kernels compiled in the devel stage,
# runtime stage stays slim.
#
# IMPORTANT: build on native amd64 (CI / x86 box). Building on Apple Silicon via
# buildx runs under QEMU: CUDA compilation is extremely slow AND a CPU-only
# fallback built that way lacks AVX2 (≈150 s/request vs ≈20 s native).

# ── Stage 1: compile llama-cpp-python with CUDA (sm_75) ───────────────────────
FROM nvidia/cuda:11.8.0-devel-ubuntu20.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y python3 python3-pip build-essential git && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir cmake ninja scikit-build-core

# CUDA_ARCHITECTURES=75 pins the T4 kernel target. (Do NOT add the deprecated
# LLAMA_CUBLAS flag — recent llama.cpp fails the configure step on it.)
RUN CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=75" \
    FORCE_CMAKE=1 \
    pip3 wheel --no-deps -w /wheels "llama-cpp-python<0.3.0"

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM nvidia/cuda:11.8.0-runtime-ubuntu20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
RUN pip3 install --no-cache-dir /wheels/*.whl && rm -rf /wheels

RUN pip3 install --no-cache-dir \
    "flask>=3.0.0" \
    "pydantic>=2.8.0" \
    "prometheus-client>=0.19.0"

RUN python3 -c "from llama_cpp import Llama"

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
