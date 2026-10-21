variable "cloudflare_account_id" {
  description = "Cloudflare account that owns the Worker, D1, R2 and queue"
  type        = string
}

variable "cloudflare_zone_id" {
  description = "Zone for the Worker's custom domains (heartbeatchurch.com.au)"
  type        = string
}

variable "worker_name" {
  description = "Worker script name; must match env.production.name in manifests/pulse-v2/wrangler.jsonc"
  type        = string
  default     = "pulse"
}

variable "hostname" {
  description = "Custom domain served by the Worker; also its PUBLIC_ORIGIN (sign-in redirects, email links)"
  type        = string
}

variable "google_project_id" {
  description = "Google Cloud project that owns the Drive service account (GDRIVE_SA_* secrets)"
  type        = string
}
