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

output "web_bucket_name" {
  description = "Managed S3 bucket for the static web build."
  value       = try(aws_s3_bucket.web[0].bucket, null)
}

output "web_distribution_id" {
  description = "CloudFront distribution ID for the web app."
  value       = try(aws_cloudfront_distribution.web[0].id, null)
}

output "web_distribution_domain_name" {
  description = "CloudFront hostname for the web app."
  value       = try(aws_cloudfront_distribution.web[0].domain_name, null)
}

output "web_url" {
  description = "Primary public URL for the web app."
  value       = local.web_url
}

output "api_ecr_repository_url" {
  description = "ECR repository URL that stores the API image."
  value       = try(local.api_image_repository_url, null)
}

output "api_service_id" {
  description = "App Runner service ID for the API."
  value       = try(aws_apprunner_service.api[0].service_id, null)
}

output "api_service_arn" {
  description = "App Runner service ARN for the API."
  value       = try(aws_apprunner_service.api[0].arn, null)
}

output "api_service_url" {
  description = "App Runner default service URL."
  value       = try("https://${aws_apprunner_service.api[0].service_url}", null)
}

output "api_url" {
  description = "Primary public URL for the API."
  value       = local.api_url
}

output "api_custom_domain_dns_target" {
  description = "DNS target returned by the App Runner custom domain association."
  value       = try(aws_apprunner_custom_domain_association.api[0].dns_target, null)
}

output "api_custom_domain_validation_records" {
  description = "Certificate validation records for the App Runner custom domain."
  value       = try(aws_apprunner_custom_domain_association.api[0].certificate_validation_records, null)
}
