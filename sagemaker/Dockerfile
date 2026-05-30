# GPU-capable SageMaker inference container for text2sql GGUF model
# Build context: repo root (needs models/ and sagemaker/)
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y python3 python3-pip gcc g++ cmake && \
    rm -rf /var/lib/apt/lists/*

# Compile llama-cpp-python with CUDA support
RUN CMAKE_ARGS="-DGGML_CUDA=on" pip3 install --no-cache-dir \
    "llama-cpp-python<0.3.0" \
    "flask>=3.0.0" \
    "pydantic>=2.8.0"

# Model baked into image (avoids runtime download, same pattern as Lambda)
COPY models/model_q4_k_m.gguf /opt/ml/model/model_q4_k_m.gguf

COPY sagemaker/serve.py /serve.py
COPY sagemaker/prompts.py /prompts.py

ENV GGUF_PATH=/opt/ml/model/model_q4_k_m.gguf
ENV MODEL_N_CTX=512
ENV MODEL_N_THREADS=4

EXPOSE 8080
CMD ["python3", "/serve.py"]
