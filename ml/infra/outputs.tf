output "mlflow_artifacts_bucket" {
  value = aws_s3_bucket.mlflow_artifacts.bucket
}

output "dataset_bucket" {
  value = aws_s3_bucket.dataset.bucket
}
