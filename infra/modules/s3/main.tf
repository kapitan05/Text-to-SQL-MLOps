resource "aws_s3_bucket" "failed_sql" {
  bucket = "${var.project}-failed-sql"
}
