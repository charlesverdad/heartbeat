variable "environment" {
  description = "Environment name (dev, prod, etc.)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "vm-pulse"
}

variable "vm_resource_group_name" {
  description = "Name of the VM's resource group"
  type        = string
}

variable "vm_managed_identity_name" {
  description = "Name of the VM's managed identity"
  type        = string
}

variable "cloudflare_account_id" {
  description = "Cloudflare account ID for tunnel management"
  type        = string
}

variable "cloudflare_zone_id" {
  description = "Cloudflare zone ID for DNS record management"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the website"
  type        = string
  default     = "pulse.heartbeatchurch.com.au"
}

# Application secrets
variable "session_secret" {
  description = "Secret key for session signing (openssl rand -hex 32)"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "PostgreSQL database password"
  type        = string
  sensitive   = true
}

variable "google_client_id" {
  description = "Google OAuth 2.0 client ID"
  type        = string
  sensitive   = true
}

variable "google_client_secret" {
  description = "Google OAuth 2.0 client secret"
  type        = string
  sensitive   = true
}

variable "vapid_public_key" {
  description = "VAPID public key for web push notifications"
  type        = string
  sensitive   = true
}

variable "vapid_private_key" {
  description = "VAPID private key for web push notifications"
  type        = string
  sensitive   = true
}

variable "smtp_pass" {
  description = "Google App Password for SMTP email"
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "vm-hb-pulse"
    ManagedBy   = "terraform"
    Environment = "prod"
  }
}
