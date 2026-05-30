.PHONY: init validate plan apply destroy

TF_STATE_BUCKET ?= $(error TF_STATE_BUCKET is required, e.g. make init TF_STATE_BUCKET=my-tf-state)

init:
	terraform init -backend-config="bucket=$(TF_STATE_BUCKET)"

validate:
	terraform validate

plan:
	terraform plan

apply:
	@read -p "Apply ML infra changes? [y/N] " confirm && [ "$$confirm" = "y" ]
	terraform apply

destroy:
	@read -p "DESTROY ML infra? [y/N] " confirm && [ "$$confirm" = "y" ]
	terraform destroy
