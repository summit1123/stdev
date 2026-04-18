locals {
  name_prefix = "${var.project_name}-${var.environment}"

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
