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
