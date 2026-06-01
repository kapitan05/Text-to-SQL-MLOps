variable "project" {
  type = string
}

variable "sagemaker_image_uri" {
  type        = string
  description = "ECR image URI for the SageMaker inference container"
}

variable "pushgateway_url" {
  type        = string
  description = "URL of the Pushgateway on the monitoring EC2 instance"
}
