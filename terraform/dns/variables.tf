variable "environment" {
  description = "Environment name (dev, prod, etc.)"
  type        = string
  default     = "prod"
}

variable "cloudflare_zone_id" {
  description = "Cloudflare zone ID for heartbeatchurch.com.au"
  type        = string
}

variable "ipt_ip_address" {
  description = "IPv4 address the ipt subdomain points to (Lovable hosting)"
  type        = string
}

variable "ipt_lovable_verify" {
  description = "Lovable domain verification token for the ipt subdomain"
  type        = string
}
