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

output "monitoring_pushgateway_url" {
  description = "Pushgateway URL — set as PUSHGATEWAY_URL in Lambda and SageMaker"
  value       = module.monitoring.pushgateway_url
}

output "monitoring_grafana_url" {
  description = "Grafana UI (admin / <grafana_password>)"
  value       = module.monitoring.grafana_url
}

output "monitoring_public_ip" {
  description = "Elastic IP of the monitoring EC2 instance"
  value       = module.monitoring.public_ip
}

output "monitoring_mlflow_url" {
  description = "MLflow tracking server URL"
  value       = module.monitoring.mlflow_url
}
