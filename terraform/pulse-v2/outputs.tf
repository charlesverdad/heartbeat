output "d1_database_id" {
  description = "D1 id for wrangler.jsonc (deploy.sh fills it in)"
  value       = cloudflare_d1_database.pulse.id
}

output "oauth_kv_id" {
  description = "OAUTH_KV namespace id for wrangler.jsonc (deploy.sh fills it in)"
  value       = cloudflare_workers_kv_namespace.oauth.id
}

output "public_origin" {
  description = "PUBLIC_ORIGIN for the Worker; register <origin>/auth/callback on the Google OAuth client"
  value       = "https://${var.hostname}"
}

output "resend_domain_status" {
  description = "Resend's verification status for the sending domain"
  value       = resend_domain_verification.mail.status
}

output "resend_api_key" {
  description = "Send-only Resend key for the Worker's RESEND_API_KEY (secrets.sh uploads it)"
  value       = resend_api_key.pulse.token
  sensitive   = true
}

output "resend_webhook_secret" {
  description = "Signing secret for the Worker's RESEND_WEBHOOK_SECRET (secrets.sh uploads it)"
  value       = resend_webhook.pulse.signing_secret
  sensitive   = true
}
