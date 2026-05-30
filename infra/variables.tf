variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "text2sql"
}

variable "ecr_image_uri" {
  type        = string
  description = "ECR image URI for the Lambda container (e.g. 123456789012.dkr.ecr.us-east-1.amazonaws.com/text2sql-lambda:latest)"
}

variable "sagemaker_image_uri" {
  type        = string
  description = "ECR image URI for the SageMaker inference container (e.g. 123456789012.dkr.ecr.us-east-1.amazonaws.com/text2sql-sagemaker:latest)"
}
