output "endpoint_name" {
  value = aws_sagemaker_endpoint.inference.name
}

output "endpoint_arn" {
  value = aws_sagemaker_endpoint.inference.arn
}
