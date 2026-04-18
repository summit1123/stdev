data "aws_ami" "ubuntu_2404" {
  count       = var.create_ec2_runtime ? 1 : 0
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

data "aws_iam_policy_document" "runtime_ssm_parameters" {
  count = var.create_ec2_runtime ? 1 : 0

  statement {
    sid    = "ReadRuntimeParameters"
    effect = "Allow"

    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParametersByPath",
    ]

    resources = [
      "arn:${data.aws_partition.current.partition}:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${local.ec2_ssm_parameter_prefix}*",
    ]
  }
}

resource "aws_iam_policy" "runtime_ssm_parameters" {
  count = var.create_ec2_runtime ? 1 : 0

  name        = "${local.name_prefix}-runtime-ssm"
  description = "Read runtime secrets for the kwail EC2 host."
  policy      = data.aws_iam_policy_document.runtime_ssm_parameters[0].json
}

data "aws_iam_policy_document" "runtime_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "runtime" {
  count = var.create_ec2_runtime ? 1 : 0

  name               = "${local.name_prefix}-runtime"
  assume_role_policy = data.aws_iam_policy_document.runtime_assume_role.json
}

resource "aws_iam_role_policy_attachment" "runtime_ssm_managed" {
  count = var.create_ec2_runtime ? 1 : 0

  role       = aws_iam_role.runtime[0].name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "runtime_media_rw" {
  count = var.create_ec2_runtime && var.create_media_bucket && var.create_media_access_policy ? 1 : 0

  role       = aws_iam_role.runtime[0].name
  policy_arn = aws_iam_policy.media_rw[0].arn
}

resource "aws_iam_role_policy_attachment" "runtime_ssm_parameters" {
  count = var.create_ec2_runtime ? 1 : 0

  role       = aws_iam_role.runtime[0].name
  policy_arn = aws_iam_policy.runtime_ssm_parameters[0].arn
}

resource "aws_iam_instance_profile" "runtime" {
  count = var.create_ec2_runtime ? 1 : 0

  name = "${local.name_prefix}-runtime"
  role = aws_iam_role.runtime[0].name
}

resource "aws_security_group" "runtime" {
  count = var.create_ec2_runtime ? 1 : 0

  name        = "${local.name_prefix}-runtime"
  description = "Inbound access for the kwail runtime host."
  vpc_id      = local.ec2_vpc_id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.ec2_allowed_http_cidrs
  }

  dynamic "ingress" {
    for_each = length(var.ec2_allowed_https_cidrs) > 0 ? [1] : []

    content {
      description = "HTTPS"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = var.ec2_allowed_https_cidrs
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "runtime" {
  count = var.create_ec2_runtime ? 1 : 0

  ami                    = data.aws_ami.ubuntu_2404[0].id
  instance_type          = var.ec2_instance_type
  subnet_id              = local.ec2_subnet_id
  iam_instance_profile   = aws_iam_instance_profile.runtime[0].name
  vpc_security_group_ids = [aws_security_group.runtime[0].id]

  user_data = templatefile("${path.module}/templates/ec2_user_data.sh.tftpl", {
    deploy_user           = var.ec2_deploy_user
    project_root          = var.ec2_project_root
    repo_url              = var.ec2_repo_url
    repo_branch           = var.ec2_repo_branch
    web_domain            = var.web_domain != null ? var.web_domain : ""
    api_domain            = var.api_domain != null ? var.api_domain : ""
    aws_region            = var.aws_region
    media_bucket_name     = var.create_media_bucket ? local.media_bucket_name : ""
    media_public_base_url = local.media_public_base_url != null ? local.media_public_base_url : ""
    parameter_prefix      = local.ec2_ssm_parameter_prefix
  })

  root_block_device {
    volume_size           = var.ec2_root_volume_size
    volume_type           = var.ec2_root_volume_type
    delete_on_termination = true
    encrypted             = true
  }
}

resource "aws_eip" "runtime" {
  count = var.create_ec2_runtime && var.ec2_create_eip ? 1 : 0

  domain   = "vpc"
  instance = aws_instance.runtime[0].id
}
