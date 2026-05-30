# Lightweight Lambda image — model moved to SageMaker endpoint
FROM public.ecr.aws/lambda/python:3.11

RUN yum update -y && yum install -y libgomp && yum clean all

RUN pip install --no-cache-dir uv

WORKDIR /build
COPY pyproject.toml ./

RUN uv pip install --system --target ${LAMBDA_TASK_ROOT} \
        "pydantic>=2.8.0" \
        "boto3>=1.35.0" \
        "tenacity>=8.5.0"

COPY src/ ${LAMBDA_TASK_ROOT}/src/

ENV SAGEMAKER_ENDPOINT_NAME=text2sql-inference

CMD ["src.handler.lambda_handler"]
