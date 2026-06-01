module "s3" {
  source  = "./modules/s3"
  project = var.project
}

module "kinesis" {
  source  = "./modules/kinesis"
  project = var.project
}

module "dynamodb" {
  source  = "./modules/dynamodb"
  project = var.project
}

module "monitoring" {
  source                = "./modules/monitoring"
  project               = var.project
  grafana_password      = var.grafana_password
  key_name              = var.key_name
  admin_cidr_blocks     = var.admin_cidr_blocks
  dynamodb_table_arn    = module.dynamodb.table_arn
  failed_sql_bucket_arn = module.s3.failed_sql_bucket_arn
}

module "sagemaker" {
  source              = "./modules/sagemaker"
  project             = var.project
  sagemaker_image_uri = var.sagemaker_image_uri
  pushgateway_url     = module.monitoring.pushgateway_url
}

module "lambda" {
  source                  = "./modules/lambda"
  project                 = var.project
  ecr_image_uri           = var.ecr_image_uri
  kinesis_stream_arn      = module.kinesis.stream_arn
  failed_sql_bucket       = module.s3.failed_sql_bucket
  failed_sql_bucket_arn   = module.s3.failed_sql_bucket_arn
  dynamodb_table_name     = module.dynamodb.table_name
  dynamodb_table_arn      = module.dynamodb.table_arn
  sagemaker_endpoint_name = module.sagemaker.endpoint_name
  sagemaker_endpoint_arn  = module.sagemaker.endpoint_arn
  pushgateway_url         = module.monitoring.pushgateway_url
}

module "api_gateway" {
  source              = "./modules/api_gateway"
  project             = var.project
  aws_region          = var.aws_region
  kinesis_stream_name = module.kinesis.stream_name
  kinesis_stream_arn  = module.kinesis.stream_arn
}
