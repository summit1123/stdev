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
