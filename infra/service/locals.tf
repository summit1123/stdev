locals {
  name_prefix             = "${var.project_name}-${var.environment}"
  media_bucket_name       = coalesce(var.media_bucket_name, "${local.name_prefix}-media")
  web_bucket_name         = coalesce(var.web_bucket_name, "${local.name_prefix}-web")
  api_ecr_repository_name = coalesce(var.api_ecr_repository_name, "${local.name_prefix}-api")
  api_service_name        = coalesce(var.api_service_name, "${local.name_prefix}-api")
  api_image_repository_url = coalesce(
    var.api_image_repository_url,
    try(aws_ecr_repository.api[0].repository_url, null),
  )
  web_aliases = (
    var.web_domain != null && var.web_acm_certificate_arn != null
    ? [var.web_domain]
    : []
  )
  media_public_base_url = (
    var.create_media_bucket && var.media_bucket_public_read_enabled
    ? (
      var.aws_region == "us-east-1"
      ? "https://${local.media_bucket_name}.s3.amazonaws.com"
      : "https://${local.media_bucket_name}.s3.${var.aws_region}.amazonaws.com"
    )
    : null
  )
  api_runtime_environment_default = {
    APP_ENV               = "production"
    CORS_ORIGIN           = var.web_domain != null ? "https://${var.web_domain}" : ""
    MEDIA_STORAGE_BACKEND = var.create_media_bucket ? "s3" : "local"
    MEDIA_S3_BUCKET       = var.create_media_bucket ? local.media_bucket_name : ""
    MEDIA_S3_REGION       = var.aws_region
    MEDIA_S3_PREFIX       = "media"
    MEDIA_S3_PUBLIC_BASE_URL = (
      local.media_public_base_url != null
      ? local.media_public_base_url
      : ""
    )
  }
  api_runtime_environment = {
    for key, value in merge(local.api_runtime_environment_default, var.api_runtime_environment) :
    key => value
    if value != null && trimspace(value) != ""
  }
  api_runtime_policy_arns = concat(
    var.api_runtime_policy_arns,
    var.create_media_bucket && var.create_media_access_policy ? [aws_iam_policy.media_rw[0].arn] : [],
  )
  web_url = (
    var.web_domain != null
    ? "https://${var.web_domain}"
    : try("https://${aws_cloudfront_distribution.web[0].domain_name}", null)
  )
  api_url = (
    var.api_domain != null
    ? "https://${var.api_domain}"
    : try("https://${aws_apprunner_service.api[0].service_url}", null)
  )

  default_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Repository  = "stdev"
      Stack       = "service"
    },
    var.app_tags
  )
}
