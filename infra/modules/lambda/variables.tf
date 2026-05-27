variable "project" {
  type = string
}

variable "ecr_image_uri" {
  type        = string
  description = "ECR image URI including tag"
}

variable "kinesis_stream_arn" {
  type = string
}

variable "failed_sql_bucket" {
  type = string
}

variable "failed_sql_bucket_arn" {
  type = string
}

variable "dynamodb_table_name" {
  type = string
}

variable "dynamodb_table_arn" {
  type = string
}
