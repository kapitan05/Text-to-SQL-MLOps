resource "aws_vpc" "custom_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = { Name = "${var.project}-vpc" }
}

resource "aws_subnet" "public_subnet" {
  vpc_id                  = aws_vpc.custom_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.project}-public-subnet" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.custom_vpc.id

  tags = {
    Name = "${var.project}-igw"
  }
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.custom_vpc.id

  route {
    cidr_block = "0.0.0.0/0" # This means "all outside internet traffic"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "${var.project}-public-rt"
  }
}

resource "aws_route_table_association" "public_rta" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public_rt.id
}

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
  vpc_id                = aws_vpc.custom_vpc.id
  subnet_id             = aws_subnet.public_subnet.id
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
