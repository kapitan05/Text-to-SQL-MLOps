.PHONY: init validate plan apply destroy outputs

TF_STATE_BUCKET    ?= $(error TF_STATE_BUCKET is required)
ECR_IMAGE_URI      ?= $(error ECR_IMAGE_URI is required)
SAGEMAKER_IMAGE_URI ?= $(error SAGEMAKER_IMAGE_URI is required)
GRAFANA_PASSWORD   ?= $(error GRAFANA_PASSWORD is required)

TF_VARS := -var="ecr_image_uri=$(ECR_IMAGE_URI)" \
           -var="sagemaker_image_uri=$(SAGEMAKER_IMAGE_URI)" \
           -var="grafana_password=$(GRAFANA_PASSWORD)"

init:
	terraform init -backend-config="bucket=$(TF_STATE_BUCKET)"

validate:
	terraform validate

plan:
	terraform plan $(TF_VARS)

apply:
	@read -p "Deploy to PROD? [y/N] " confirm && [ "$$confirm" = "y" ]
	terraform apply $(TF_VARS)

destroy:
	@read -p "DESTROY prod infra? [y/N] " confirm && [ "$$confirm" = "y" ]
	terraform destroy $(TF_VARS)

outputs:
	terraform output
