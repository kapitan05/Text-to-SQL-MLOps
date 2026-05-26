# Stage 1 — compile llama-cpp-python (requires gcc/g++/cmake)
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ cmake make \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /build
COPY pyproject.toml ./

RUN uv pip install --system --target /packages \
        "llama-cpp-python>=0.2.0" \
        "pydantic>=2.8.0" \
        "boto3>=1.35.0" \
        "tenacity>=8.5.0"

# Stage 2 — clean Lambda image
FROM public.ecr.aws/lambda/python:3.11

RUN yum update -y && yum install -y libgomp && yum clean all

COPY --from=builder /packages ${LAMBDA_TASK_ROOT}
COPY src/ ${LAMBDA_TASK_ROOT}/src/
# Rename the GGUF file to a stable path; override via GGUF_PATH env var if needed
COPY models/ /opt/models/

ENV GGUF_PATH=/opt/models/model_q4_k_m.gguf.11DBF86a
ENV MODEL_N_CTX=1024
ENV MODEL_N_THREADS=4

CMD ["src.handler.lambda_handler"]
