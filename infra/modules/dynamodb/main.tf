resource "aws_dynamodb_table" "query_results" {
  name         = "query_results"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "query_id"

  attribute {
    name = "query_id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
}
