output "stream_name" {
  value = aws_kinesis_stream.queries.name
}

output "stream_arn" {
  value = aws_kinesis_stream.queries.arn
}
