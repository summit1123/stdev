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

variable "app_tags" {
  description = "Extra tags shared by all managed resources."
  type        = map(string)
  default     = {}
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
