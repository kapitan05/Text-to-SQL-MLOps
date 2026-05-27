resource "aws_s3_bucket" "mlflow_artifacts" {
  bucket = "${var.project}-mlflow-artifacts"
}

resource "aws_s3_bucket" "dataset" {
  bucket = "${var.project}-dataset-maksim-prod"
}
