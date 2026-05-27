resource "aws_kinesis_stream" "queries" {
  name        = "${var.project}-queries"
  shard_count = 1
}

resource "aws_cloudwatch_metric_alarm" "iterator_age" {
  alarm_name          = "${var.project}-kinesis-iterator-age"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "GetRecords.IteratorAgeMilliseconds"
  namespace           = "AWS/Kinesis"
  period              = 60
  statistic           = "Maximum"
  threshold           = var.iterator_age_alarm_threshold_ms
  alarm_description   = "Lambda falling behind on Kinesis stream"

  dimensions = {
    StreamName = aws_kinesis_stream.queries.name
  }
}
