output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.pulse.name
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = azurerm_key_vault.pulse.vault_uri
}

output "cloudflare_tunnel_id" {
  description = "Cloudflare tunnel ID"
  value       = cloudflare_zero_trust_tunnel_cloudflared.pulse.id
}

output "cloudflare_tunnel_cname" {
  description = "Cloudflare tunnel CNAME"
  value       = cloudflare_zero_trust_tunnel_cloudflared.pulse.cname
}

output "domain_name" {
  description = "Domain name for the website"
  value       = var.domain_name
}

output "google_drive_service_account_email" {
  description = "Share Drive folders with this service account email to allow Pulse folder listing"
  value       = google_service_account.pulse_drive.email
}

output "dns_record_id" {
  description = "Cloudflare DNS record ID"
  value       = cloudflare_record.pulse.id
}
