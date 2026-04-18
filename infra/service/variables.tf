variable "project_name" {
  description = "Short project name used in tags and resource names."
  type        = string
}

variable "environment" {
  description = "Environment name for this single-stack setup."
  type        = string
  default     = "hackathon"
}

variable "aws_region" {
  description = "Primary AWS region for the service."
  type        = string
  default     = "ap-northeast-2"
}

variable "aws_profile" {
  description = "Optional AWS CLI profile name."
  type        = string
  default     = null
}

variable "hosted_zone_name" {
  description = "Route53 hosted zone name without wildcard."
  type        = string
  default     = null
}

variable "web_domain" {
  description = "Public web domain for the app."
  type        = string
  default     = null
}

variable "api_domain" {
  description = "Public API domain for the app."
  type        = string
  default     = null
}

variable "web_acm_certificate_arn" {
  description = "Optional ACM certificate ARN in us-east-1 for the web CloudFront distribution."
  type        = string
  default     = null
}

variable "app_tags" {
  description = "Extra tags shared by all managed resources."
  type        = map(string)
  default     = {}
}

variable "create_web_bucket" {
  description = "Whether Terraform should manage the web asset bucket."
  type        = bool
  default     = true
}

variable "web_bucket_name" {
  description = "Optional explicit S3 bucket name for the web build."
  type        = string
  default     = null
}

variable "web_bucket_force_destroy" {
  description = "Allow Terraform to destroy the web bucket even when it contains objects."
  type        = bool
  default     = false
}

variable "create_web_cdn" {
  description = "Whether Terraform should manage the CloudFront distribution for the web app."
  type        = bool
  default     = true
}

variable "create_web_dns_record" {
  description = "Whether Terraform should create Route53 alias records for the web domain."
  type        = bool
  default     = false
}

variable "web_default_root_object" {
  description = "Default document served by CloudFront."
  type        = string
  default     = "index.html"
}

variable "web_error_document" {
  description = "Document returned for SPA-style 403/404 fallback handling."
  type        = string
  default     = "/index.html"
}

variable "web_price_class" {
  description = "CloudFront price class for the web distribution."
  type        = string
  default     = "PriceClass_200"
}

variable "create_media_bucket" {
  description = "Whether Terraform should manage the app media bucket."
  type        = bool
  default     = true
}

variable "media_bucket_name" {
  description = "Optional explicit S3 bucket name for uploaded and generated media."
  type        = string
  default     = null
}

variable "media_bucket_force_destroy" {
  description = "Allow Terraform to destroy the media bucket even when it contains objects."
  type        = bool
  default     = false
}

variable "media_bucket_public_read_enabled" {
  description = "Allow direct public GET access to objects when using raw S3 URLs."
  type        = bool
  default     = false
}

variable "media_bucket_expiration_days" {
  description = "Optional lifecycle expiration for media objects."
  type        = number
  default     = null
}

variable "media_bucket_cors_allowed_origins" {
  description = "Origins allowed to read media directly from S3."
  type        = list(string)
  default     = []
}

variable "media_bucket_cors_allowed_methods" {
  description = "HTTP methods allowed by the media bucket CORS rule."
  type        = list(string)
  default     = ["GET", "HEAD"]
}

variable "create_media_access_policy" {
  description = "Whether Terraform should create a reusable IAM policy for media read/write access."
  type        = bool
  default     = true
}

variable "create_api_ecr_repository" {
  description = "Whether Terraform should manage the API ECR repository."
  type        = bool
  default     = true
}

variable "api_ecr_repository_name" {
  description = "Optional explicit ECR repository name for the API image."
  type        = string
  default     = null
}

variable "api_image_repository_url" {
  description = "Optional existing ECR repository URL to use instead of creating one."
  type        = string
  default     = null
}

variable "create_api_service" {
  description = "Whether Terraform should manage the App Runner API service."
  type        = bool
  default     = true
}

variable "api_service_name" {
  description = "Optional explicit App Runner service name."
  type        = string
  default     = null
}

variable "api_image_tag" {
  description = "Container image tag App Runner should pull."
  type        = string
  default     = "latest"
}

variable "api_port" {
  description = "Container port exposed by the API image."
  type        = number
  default     = 8000
}

variable "api_cpu" {
  description = "App Runner vCPU setting."
  type        = string
  default     = "1024"
}

variable "api_memory" {
  description = "App Runner memory setting."
  type        = string
  default     = "2048"
}

variable "api_health_check_path" {
  description = "HTTP path used by App Runner health checks."
  type        = string
  default     = "/health"
}

variable "api_auto_deployments_enabled" {
  description = "Let App Runner auto-deploy when a new image is pushed to the watched tag."
  type        = bool
  default     = true
}

variable "api_runtime_environment" {
  description = "Plaintext runtime environment variables for the API service."
  type        = map(string)
  default     = {}
}

variable "api_runtime_secret_arns" {
  description = "Runtime secret environment variables for the API service, mapped as ENV_NAME => ARN."
  type        = map(string)
  default     = {}
}

variable "api_runtime_policy_arns" {
  description = "Extra IAM policy ARNs to attach to the App Runner instance role."
  type        = list(string)
  default     = []
}

variable "create_api_custom_domain" {
  description = "Whether Terraform should create an App Runner custom domain association."
  type        = bool
  default     = false
}
