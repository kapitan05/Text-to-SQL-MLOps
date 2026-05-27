output "api_endpoint" {
  description = "POST /query endpoint"
  value       = module.api_gateway.api_endpoint
}

output "kinesis_stream_name" {
  value = module.kinesis.stream_name
}

output "lambda_function_name" {
  value = module.lambda.function_name
}

output "failed_sql_bucket" {
  value = module.s3.failed_sql_bucket
}

output "dynamodb_table_name" {
  value = module.dynamodb.table_name
}
