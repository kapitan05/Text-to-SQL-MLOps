data "aws_iam_policy_document" "apigw_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "apigw_kinesis" {
  name               = "${var.project}-apigw-kinesis"
  assume_role_policy = data.aws_iam_policy_document.apigw_assume.json
}

data "aws_iam_policy_document" "apigw_kinesis" {
  statement {
    actions   = ["kinesis:PutRecord"]
    resources = [var.kinesis_stream_arn]
  }
}

resource "aws_iam_role_policy" "apigw_kinesis" {
  name   = "${var.project}-apigw-kinesis"
  role   = aws_iam_role.apigw_kinesis.id
  policy = data.aws_iam_policy_document.apigw_kinesis.json
}

resource "aws_api_gateway_rest_api" "text2sql" {
  name = "${var.project}-api"
}

resource "aws_api_gateway_resource" "query" {
  rest_api_id = aws_api_gateway_rest_api.text2sql.id
  parent_id   = aws_api_gateway_rest_api.text2sql.root_resource_id
  path_part   = "query"
}

resource "aws_api_gateway_method" "post_query" {
  rest_api_id   = aws_api_gateway_rest_api.text2sql.id
  resource_id   = aws_api_gateway_resource.query.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "kinesis_put_record" {
  rest_api_id             = aws_api_gateway_rest_api.text2sql.id
  resource_id             = aws_api_gateway_resource.query.id
  http_method             = aws_api_gateway_method.post_query.http_method
  type                    = "AWS"
  integration_http_method = "POST"
  uri                     = "arn:aws:apigateway:${var.aws_region}:kinesis:action/PutRecord"
  credentials             = aws_iam_role.apigw_kinesis.arn

  request_templates = {
    "application/json" = <<-EOT
      {
        "StreamName": "${var.kinesis_stream_name}",
        "Data": "$util.base64Encode($input.body)",
        "PartitionKey": "$context.requestId"
      }
    EOT
  }
}

resource "aws_api_gateway_method_response" "post_query_200" {
  rest_api_id = aws_api_gateway_rest_api.text2sql.id
  resource_id = aws_api_gateway_resource.query.id
  http_method = aws_api_gateway_method.post_query.http_method
  status_code = "200"
}

resource "aws_api_gateway_integration_response" "post_query_200" {
  rest_api_id = aws_api_gateway_rest_api.text2sql.id
  resource_id = aws_api_gateway_resource.query.id
  http_method = aws_api_gateway_method.post_query.http_method
  status_code = aws_api_gateway_method_response.post_query_200.status_code

  response_templates = {
    "application/json" = "{\"query_id\": \"$context.requestId\"}"
  }

  depends_on = [aws_api_gateway_integration.kinesis_put_record]
}

resource "aws_api_gateway_deployment" "text2sql" {
  rest_api_id = aws_api_gateway_rest_api.text2sql.id

  depends_on = [
    aws_api_gateway_integration.kinesis_put_record,
    aws_api_gateway_integration_response.post_query_200,
  ]

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.text2sql.id
  rest_api_id   = aws_api_gateway_rest_api.text2sql.id
  stage_name    = "prod"
}
