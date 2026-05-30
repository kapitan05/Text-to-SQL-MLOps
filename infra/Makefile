.PHONY: init validate plan apply destroy

TF_STATE_BUCKET ?= $(error TF_STATE_BUCKET is required, e.g. make init TF_STATE_BUCKET=my-tf-state)
ECR_IMAGE_URI   ?= $(error ECR_IMAGE_URI is required, e.g. make plan ECR_IMAGE_URI=123.dkr.ecr.eu-north-1.amazonaws.com/text2sql:latest)

TF_VARS := -var="ecr_image_uri=$(ECR_IMAGE_URI)"

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
