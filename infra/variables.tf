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
  description = "ECR image URI for the Lambda container"
}

variable "sagemaker_image_uri" {
  type        = string
  description = "ECR image URI for the SageMaker inference container"
}

variable "grafana_password" {
  type        = string
  sensitive   = true
  description = "Grafana admin password for the monitoring EC2 instance"
}

variable "key_name" {
  type        = string
  default     = ""
  description = "EC2 key pair name for SSH access to the monitoring instance (optional)"
}

variable "admin_cidr_blocks" {
  type        = list(string)
  default     = ["0.0.0.0/0"]
  description = "CIDRs for SSH and Prometheus UI access — restrict to your IP"
}
