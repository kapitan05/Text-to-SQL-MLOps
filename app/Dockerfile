# Stage 1 — compile llama-cpp-python natively for Amazon Linux
FROM public.ecr.aws/lambda/python:3.11 AS builder

# Amazon Linux uses yum instead of apt-get
RUN yum update -y && \
    yum install -y gcc gcc-c++ make cmake && \
    yum clean all

RUN pip install --no-cache-dir uv

WORKDIR /build
COPY pyproject.toml ./

RUN uv pip install --system --target /packages \
        "numpy<2.0.0" \
        "llama-cpp-python<0.3.0" \
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

ENV GGUF_PATH=/opt/models/model_q4_k_m.gguf
ENV MODEL_N_CTX=256
ENV MODEL_N_THREADS=2

CMD ["src.handler.lambda_handler"]
