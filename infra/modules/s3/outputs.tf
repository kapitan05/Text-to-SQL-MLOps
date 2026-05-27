output "failed_sql_bucket" {
  value = aws_s3_bucket.failed_sql.bucket
}

output "failed_sql_bucket_arn" {
  value = aws_s3_bucket.failed_sql.arn
}

output "mlflow_artifacts_bucket" {
  value = aws_s3_bucket.mlflow_artifacts.bucket
}

output "dataset_bucket" {
  value = aws_s3_bucket.dataset.bucket
}
