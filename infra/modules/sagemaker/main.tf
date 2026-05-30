data "aws_iam_policy_document" "sagemaker_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["sagemaker.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sagemaker" {
  name               = "${var.project}-sagemaker"
  assume_role_policy = data.aws_iam_policy_document.sagemaker_assume_role.json
}

resource "aws_iam_role_policy_attachment" "sagemaker_full" {
  role       = aws_iam_role.sagemaker.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

resource "aws_sagemaker_model" "inference" {
  name               = "${var.project}-inference"
  execution_role_arn = aws_iam_role.sagemaker.arn

  primary_container {
    image = var.sagemaker_image_uri
  }
}

resource "aws_sagemaker_endpoint_configuration" "inference" {
  name = "${var.project}-inference"

  production_variants {
    variant_name           = "primary"
    model_name             = aws_sagemaker_model.inference.name
    initial_instance_count = 1
    instance_type          = "ml.m5.xlarge"
  }
}

resource "aws_sagemaker_endpoint" "inference" {
  name                 = "${var.project}-inference"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.inference.name
}
