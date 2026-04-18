locals {
  name_prefix       = "${var.project_name}-${var.environment}"
  media_bucket_name = coalesce(var.media_bucket_name, "${local.name_prefix}-media")

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
