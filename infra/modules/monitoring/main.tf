data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ── Security group ────────────────────────────────────────────────────────────

resource "aws_security_group" "monitoring" {
  name        = "${var.project}-monitoring"
  vpc_id      = var.vpc_id
  description = "Prometheus + Pushgateway + Grafana"

  # Pushgateway — Lambda and SageMaker push from the public internet
  ingress {
    description = "Pushgateway"
    from_port   = 9091
    to_port     = 9091
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Grafana UI
  ingress {
    description = "Grafana"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # MLflow tracking server
  ingress {
    description = "MLflow"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Prometheus UI (restricted)
  ingress {
    description = "Prometheus"
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = var.admin_cidr_blocks
  }

  # SSH
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.admin_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ── IAM — lets Evidently read DynamoDB and write S3 from this instance ────────

data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "monitoring" {
  name               = "${var.project}-monitoring"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

data "aws_iam_policy_document" "monitoring_perms" {
  statement {
    sid       = "DynamoRead"
    actions   = ["dynamodb:Scan", "dynamodb:GetItem", "dynamodb:Query"]
    resources = [var.dynamodb_table_arn]
  }

  statement {
    sid     = "S3ReadWrite"
    actions = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
    resources = [
      var.failed_sql_bucket_arn,
      "${var.failed_sql_bucket_arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "monitoring" {
  name   = "${var.project}-monitoring"
  role   = aws_iam_role.monitoring.id
  policy = data.aws_iam_policy_document.monitoring_perms.json
}

resource "aws_iam_instance_profile" "monitoring" {
  name = "${var.project}-monitoring"
  role = aws_iam_role.monitoring.name
}

# ── EC2 instance ──────────────────────────────────────────────────────────────

resource "aws_instance" "monitoring" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = "t3.small"
  subnet_id              = var.subnet_id
  key_name               = var.key_name != "" ? var.key_name : null
  vpc_security_group_ids = [aws_security_group.monitoring.id]
  iam_instance_profile   = aws_iam_instance_profile.monitoring.name

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    grafana_password = var.grafana_password
  })

  tags = {
    Name    = "${var.project}-monitoring"
    Project = var.project
  }
}

resource "aws_eip" "monitoring" {
  instance = aws_instance.monitoring.id
  domain   = "vpc"

  tags = {
    Name    = "${var.project}-monitoring"
    Project = var.project
  }
}
