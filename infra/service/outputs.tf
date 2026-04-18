output "account_id" {
  description = "AWS account ID used by this stack."
  value       = data.aws_caller_identity.current.account_id
}

output "current_region" {
  description = "AWS region Terraform is pointed at."
  value       = data.aws_region.current.region
}

output "hosted_zone_id" {
  description = "Selected public hosted zone ID, if configured."
  value       = try(data.aws_route53_zone.selected[0].zone_id, null)
}

output "default_tags" {
  description = "Shared default tags applied through the provider."
  value       = local.default_tags
}
