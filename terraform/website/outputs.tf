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
