output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.bookstack.name
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = azurerm_key_vault.bookstack.vault_uri
}

output "cloudflare_tunnel_id" {
  description = "Cloudflare tunnel ID"
  value       = cloudflare_zero_trust_tunnel_cloudflared.bookstack.id
}

output "cloudflare_tunnel_cname" {
  description = "Cloudflare tunnel CNAME"
  value       = cloudflare_zero_trust_tunnel_cloudflared.bookstack.cname
}

output "domain_name" {
  description = "Domain name for the website"
  value       = var.domain_name
}

output "dns_record_id" {
  description = "Cloudflare DNS record ID"
  value       = cloudflare_record.bookstack.id
}
