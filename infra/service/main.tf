data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_partition" "current" {}

data "aws_route53_zone" "selected" {
  count        = var.hosted_zone_name == null ? 0 : 1
  name         = var.hosted_zone_name
  private_zone = false
}
