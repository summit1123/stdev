data "aws_cloudfront_cache_policy" "caching_optimized" {
  count = var.create_web_cdn ? 1 : 0
  name  = "Managed-CachingOptimized"
}

resource "aws_s3_bucket" "web" {
  count = var.create_web_bucket ? 1 : 0

  bucket        = local.web_bucket_name
  force_destroy = var.web_bucket_force_destroy
}

resource "aws_s3_bucket_ownership_controls" "web" {
  count = var.create_web_bucket ? 1 : 0

  bucket = aws_s3_bucket.web[0].id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "web" {
  count = var.create_web_bucket ? 1 : 0

  bucket = aws_s3_bucket.web[0].id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "web" {
  count = var.create_web_bucket ? 1 : 0

  bucket = aws_s3_bucket.web[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "web" {
  count = var.create_web_bucket ? 1 : 0

  bucket = aws_s3_bucket.web[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_cloudfront_origin_access_control" "web" {
  count = var.create_web_bucket && var.create_web_cdn ? 1 : 0

  name                              = "${local.name_prefix}-web-oac"
  description                       = "Origin access control for the web asset bucket."
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "web" {
  count = var.create_web_bucket && var.create_web_cdn ? 1 : 0

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${local.name_prefix} web distribution"
  default_root_object = var.web_default_root_object
  price_class         = var.web_price_class
  aliases             = local.web_aliases

  origin {
    domain_name              = aws_s3_bucket.web[0].bucket_regional_domain_name
    origin_id                = "web-s3-origin"
    origin_access_control_id = aws_cloudfront_origin_access_control.web[0].id
  }

  default_cache_behavior {
    target_origin_id       = "web-s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD", "OPTIONS"]
    cache_policy_id        = data.aws_cloudfront_cache_policy.caching_optimized[0].id
    compress               = true
  }

  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = var.web_error_document
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = var.web_error_document
    error_caching_min_ttl = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = length(local.web_aliases) == 0
    acm_certificate_arn            = length(local.web_aliases) > 0 ? var.web_acm_certificate_arn : null
    ssl_support_method             = length(local.web_aliases) > 0 ? "sni-only" : null
    minimum_protocol_version       = length(local.web_aliases) > 0 ? "TLSv1.2_2021" : null
  }
}

data "aws_iam_policy_document" "web_bucket_policy" {
  count = var.create_web_bucket && var.create_web_cdn ? 1 : 0

  statement {
    sid    = "AllowCloudFrontReadAccess"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    actions = ["s3:GetObject"]

    resources = [
      "${aws_s3_bucket.web[0].arn}/*",
    ]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.web[0].arn]
    }
  }
}

resource "aws_s3_bucket_policy" "web" {
  count = var.create_web_bucket && var.create_web_cdn ? 1 : 0

  bucket = aws_s3_bucket.web[0].id
  policy = data.aws_iam_policy_document.web_bucket_policy[0].json
}

resource "aws_route53_record" "web_ipv4" {
  count = (
    var.create_web_dns_record &&
    var.hosted_zone_name != null &&
    var.web_domain != null &&
    var.create_web_cdn
  ) ? 1 : 0

  zone_id = data.aws_route53_zone.selected[0].zone_id
  name    = var.web_domain
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.web[0].domain_name
    zone_id                = aws_cloudfront_distribution.web[0].hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "web_ipv6" {
  count = (
    var.create_web_dns_record &&
    var.hosted_zone_name != null &&
    var.web_domain != null &&
    var.create_web_cdn
  ) ? 1 : 0

  zone_id = data.aws_route53_zone.selected[0].zone_id
  name    = var.web_domain
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.web[0].domain_name
    zone_id                = aws_cloudfront_distribution.web[0].hosted_zone_id
    evaluate_target_health = false
  }
}
