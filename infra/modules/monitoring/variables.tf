variable "project" {
  type = string
}

variable "grafana_password" {
  type        = string
  sensitive   = true
  description = "Grafana admin password"
}

variable "key_name" {
  type        = string
  default     = ""
  description = "EC2 key pair name for SSH access (leave empty to skip)"
}

variable "admin_cidr_blocks" {
  type        = list(string)
  default     = ["0.0.0.0/0"]
  description = "CIDRs allowed to reach SSH and Prometheus UI (restrict to your IP in production)"
}

variable "dynamodb_table_arn" {
  type        = string
  description = "ARN of the query_results DynamoDB table (for Evidently read access)"
}

variable "failed_sql_bucket_arn" {
  type        = string
  description = "ARN of the failed-SQL S3 bucket (for Evidently read/write access)"
}

variable "vpc_id" {
  type = string
}

variable "subnet_id" {
  type = string
}
