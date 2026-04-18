data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_partition" "current" {}

data "aws_route53_zone" "selected" {
  count        = var.hosted_zone_name == null ? 0 : 1
  name         = var.hosted_zone_name
  private_zone = false
}

data "aws_vpc" "default" {
  count   = var.create_ec2_runtime && var.ec2_vpc_id == null ? 1 : 0
  default = true
}

data "aws_subnets" "default" {
  count = var.create_ec2_runtime && var.ec2_subnet_id == null ? 1 : 0

  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default[0].id]
  }
}
