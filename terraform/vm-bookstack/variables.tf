variable "environment" {
  description = "Environment name (dev, prod, etc.)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "vm-bookstack"
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
  default     = "bookstack.heartbeatchurch.com.au"
}

# BookStack Application Secrets
variable "app_key" {
  description = "Laravel application key (base64 encoded)"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "MySQL/MariaDB password for BookStack user"
  type        = string
  sensitive   = true
}

variable "mysql_root_password" {
  description = "MySQL root password"
  type        = string
  sensitive   = true
}

# Google OAuth Configuration
variable "google_app_id" {
  description = "Google OAuth Client ID"
  type        = string
  sensitive   = true
}

variable "google_app_secret" {
  description = "Google OAuth Client Secret"
  type        = string
  sensitive   = true
}

# SMTP/Gmail Configuration
variable "mail_username" {
  description = "SMTP username (Gmail address)"
  type        = string
  sensitive   = true
}

variable "mail_password" {
  description = "SMTP password (Gmail app password)"
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "vm-bookstack"
    ManagedBy   = "terraform"
    Environment = "prod"
  }
}
