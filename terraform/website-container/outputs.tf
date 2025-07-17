output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "keyvault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.main.name
}

output "keyvault_id" {
  description = "ID of the Key Vault"
  value       = azurerm_key_vault.main.id
}

output "managed_identity_name" {
  description = "Name of the managed identity"
  value       = azurerm_user_assigned_identity.main.name
}

output "managed_identity_client_id" {
  description = "Client ID of the managed identity"
  value       = azurerm_user_assigned_identity.main.client_id
}

output "managed_identity_principal_id" {
  description = "Principal ID of the managed identity"
  value       = azurerm_user_assigned_identity.main.principal_id
}

output "container_app_environment_name" {
  description = "Name of the Container App Environment"
  value       = azurerm_container_app_environment.main.name
}

output "ghost_container_app_name" {
  description = "Name of the Ghost Container App"
  value       = azurerm_container_app.ghost.name
}

output "ghost_container_app_fqdn" {
  description = "FQDN of the Ghost Container App"
  value       = azurerm_container_app.ghost.ingress[0].fqdn
}

output "cloudflare_tunnel_container_app_name" {
  description = "Name of the Cloudflare Tunnel Container App"
  value       = azurerm_container_app.cloudflare_tunnel.name
}

# Cloudflare outputs
output "cloudflare_tunnel_id" {
  description = "Cloudflare tunnel ID"
  value       = cloudflare_zero_trust_tunnel_cloudflared.website.id
}

output "cloudflare_tunnel_cname" {
  description = "Cloudflare tunnel CNAME"
  value       = cloudflare_zero_trust_tunnel_cloudflared.website.cname
}

output "cloudflare_tunnel_token" {
  description = "Cloudflare tunnel token"
  value       = cloudflare_zero_trust_tunnel_cloudflared.website.tunnel_token
  sensitive   = true
}

output "dns_record_name" {
  description = "DNS record name"
  value       = cloudflare_record.website.name
}

output "dns_record_value" {
  description = "DNS record value"
  value       = cloudflare_record.website.value
}

output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.main.name
}

output "website_url" {
  description = "URL of the website"
  value       = "https://${var.domain_name}"
}

# MySQL outputs
output "mysql_server_name" {
  description = "Name of the MySQL server"
  value       = azurerm_mysql_flexible_server.main.name
}

output "mysql_server_fqdn" {
  description = "FQDN of the MySQL server"
  value       = azurerm_mysql_flexible_server.main.fqdn
}

output "mysql_database_name" {
  description = "Name of the MySQL database"
  value       = azurerm_mysql_flexible_database.ghost.name
}

output "mysql_admin_username" {
  description = "MySQL administrator username"
  value       = var.mysql_admin_username
}
