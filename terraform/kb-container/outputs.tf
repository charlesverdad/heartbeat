output "bookstack_url" {
  description = "URL to access BookStack"
  value       = "https://${var.domain_name}"
}

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "key_vault_name" {
  description = "Name of the Key Vault containing secrets"
  value       = azurerm_key_vault.main.name
}

output "container_app_name" {
  description = "Name of the Container App"
  value       = azurerm_container_app.bookstack.name
}

output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.main.name
}

output "cloudflare_tunnel_name" {
  description = "Name of the Cloudflare tunnel"
  value       = cloudflare_zero_trust_tunnel_cloudflared.bookstack.name
}

output "oidc_redirect_uri" {
  description = "OIDC Redirect URI to configure in Google OAuth"
  value       = "https://${var.domain_name}/login/service/oidc/callback"
}
