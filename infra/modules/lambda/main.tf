data "aws_iam_policy_document" "assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.project}-lambda"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "permissions" {
  statement {
    sid = "KinesisRead"
    actions = [
      "kinesis:GetRecords",
      "kinesis:GetShardIterator",
      "kinesis:DescribeStream",
      "kinesis:DescribeStreamSummary",
      "kinesis:ListShards",
      "kinesis:ListStreams",
    ]
    resources = [var.kinesis_stream_arn]
  }

  statement {
    sid       = "S3Write"
    actions   = ["s3:PutObject"]
    resources = ["${var.failed_sql_bucket_arn}/*"]
  }

  statement {
    sid       = "DynamoWrite"
    actions   = ["dynamodb:PutItem"]
    resources = [var.dynamodb_table_arn]
  }

  statement {
    sid       = "SageMakerInvoke"
    actions   = ["sagemaker:InvokeEndpoint"]
    resources = [var.sagemaker_endpoint_arn]
  }
}

resource "aws_iam_role_policy" "permissions" {
  name   = "${var.project}-lambda-permissions"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.permissions.json
}

resource "aws_lambda_function" "inference" {
  function_name = "${var.project}-inference"
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = var.ecr_image_uri
  timeout       = 60
  memory_size   = 256

  architectures = ["arm64"]

  reserved_concurrent_executions = 5

  environment {
    variables = {
      DYNAMODB_TABLE          = var.dynamodb_table_name
      FAILED_SQL_BUCKET       = var.failed_sql_bucket
      SAGEMAKER_ENDPOINT_NAME = var.sagemaker_endpoint_name
      PUSHGATEWAY_URL         = var.pushgateway_url
    }
  }
}

resource "aws_lambda_event_source_mapping" "kinesis" {
  event_source_arn  = var.kinesis_stream_arn
  function_name     = aws_lambda_function.inference.arn
  starting_position = "LATEST"
  batch_size        = 1
}
