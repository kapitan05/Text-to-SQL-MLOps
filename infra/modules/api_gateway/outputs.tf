output "api_endpoint" {
  description = "POST /query invoke URL"
  value       = "${aws_api_gateway_stage.prod.invoke_url}/query"
}

output "rest_api_id" {
  value = aws_api_gateway_rest_api.text2sql.id
}
