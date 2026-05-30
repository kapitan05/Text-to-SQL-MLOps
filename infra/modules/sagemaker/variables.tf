variable "project" {
  type = string
}

variable "sagemaker_image_uri" {
  type        = string
  description = "ECR image URI for the SageMaker inference container"
}
