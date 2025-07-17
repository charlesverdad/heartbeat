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
  description = "Client ID of the managed identity for pod configuration"
  value       = azurerm_user_assigned_identity.main.client_id
}

output "managed_identity_principal_id" {
  description = "Principal ID of the managed identity"
  value       = azurerm_user_assigned_identity.main.principal_id
}

output "mysql_server_name" {
  description = "Name of the MySQL server"
  value       = azurerm_mysql_flexible_server.main.name
}

output "mysql_server_fqdn" {
  description = "FQDN of the MySQL server"
  value       = azurerm_mysql_flexible_server.main.fqdn
}

output "mysql_database_name" {
  description = "Name of the Ghost database"
  value       = azurerm_mysql_flexible_database.ghost.name
}

output "mysql_admin_username" {
  description = "MySQL administrator username"
  value       = azurerm_mysql_flexible_server.main.administrator_login
}

# Cloudflare tunnel outputs (to be added when tunnel is created)
# output "cloudflare_tunnel_id" {
#   description = "Cloudflare tunnel ID"
#   value       = cloudflare_zero_trust_tunnel_cloudflared.website_dev.id
# }
#
# output "cloudflare_tunnel_cname" {
#   description = "Cloudflare tunnel CNAME"
#   value       = cloudflare_zero_trust_tunnel_cloudflared.website_dev.cname
# }
