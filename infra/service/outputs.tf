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

output "media_bucket_name" {
  description = "Managed S3 bucket for uploaded and generated media."
  value       = try(aws_s3_bucket.media[0].bucket, null)
}

output "media_bucket_arn" {
  description = "ARN of the managed media bucket."
  value       = try(aws_s3_bucket.media[0].arn, null)
}

output "media_bucket_public_base_url" {
  description = "Direct S3 base URL when using publicly readable objects."
  value = try(
    var.aws_region == "us-east-1"
    ? "https://${aws_s3_bucket.media[0].bucket}.s3.amazonaws.com"
    : "https://${aws_s3_bucket.media[0].bucket}.s3.${var.aws_region}.amazonaws.com",
    null,
  )
}

output "media_access_policy_arn" {
  description = "IAM policy ARN to attach to the API runtime role."
  value       = try(aws_iam_policy.media_rw[0].arn, null)
}
