output "function_arn" {
  value = aws_lambda_function.inference.arn
}

output "function_name" {
  value = aws_lambda_function.inference.function_name
}

output "role_arn" {
  value = aws_iam_role.lambda.arn
}
