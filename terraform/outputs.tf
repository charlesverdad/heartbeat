output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.ghost.name
}

output "container_app_url" {
  description = "URL of the Container App"
  value       = "https://${azurerm_container_app.ghost.latest_revision_fqdn}"
}

output "custom_domain_url" {
  description = "Custom domain URL for the Ghost blog"
  value       = "https://${var.subdomain}.${var.domain_name}"
}

output "mysql_server_fqdn" {
  description = "FQDN of the MySQL server"
  value       = azurerm_mysql_flexible_server.ghost.fqdn
}

output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.ghost.name
}

output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.ghost.name
}

output "cloudflare_tunnel_id" {
  description = "Cloudflare tunnel ID"
  value       = cloudflare_tunnel.ghost.id
}

output "cloudflare_tunnel_cname" {
  description = "Cloudflare tunnel CNAME"
  value       = cloudflare_tunnel.ghost.cname
}

output "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID"
  value       = azurerm_log_analytics_workspace.ghost.workspace_id
}

# Sensitive outputs
output "mysql_admin_username" {
  description = "MySQL administrator username"
  value       = var.mysql_admin_username
  sensitive   = false
}

output "storage_account_primary_endpoint" {
  description = "Primary blob storage endpoint"
  value       = azurerm_storage_account.ghost.primary_blob_endpoint
}

output "container_app_environment_name" {
  description = "Container App Environment name"
  value       = azurerm_container_app_environment.ghost.name
}
