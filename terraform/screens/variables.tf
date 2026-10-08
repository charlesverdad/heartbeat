variable "cloudflare_account_id" {
  description = "Cloudflare account ID that owns the Pages project"
  type        = string
}

variable "cloudflare_zone_id" {
  description = "Cloudflare zone ID for heartbeatchurch.com.au"
  type        = string
}

variable "project_name" {
  description = "Pages project name (also the *.pages.dev subdomain when it is free)"
  type        = string
  default     = "screens"
}

variable "domain_name" {
  description = "Custom domain the site is served on"
  type        = string
  default     = "screens.heartbeatchurch.com.au"
}

variable "production_branch" {
  description = "Deploys from this branch go to production; any other branch is a preview"
  type        = string
  default     = "main"
}
