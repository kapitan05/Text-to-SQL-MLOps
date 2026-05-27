resource "aws_s3_bucket" "failed_sql" {
  bucket = "${var.project}-failed-sql"
}

resource "aws_s3_bucket" "mlflow_artifacts" {
  bucket = "${var.project}-mlflow-artifacts"
}

resource "aws_s3_bucket" "dataset" {
  bucket = "${var.project}-dataset"
}
