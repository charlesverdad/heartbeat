# Random suffix for Key Vault name (must be globally unique)
resource "random_string" "kv_suffix" {
  length  = 8
  special = false
  upper   = false
}

# Key Vault
resource "azurerm_key_vault" "ghost" {
  name                = "${var.project_name}-${var.environment}-kv-${random_string.kv_suffix.result}"
  location            = azurerm_resource_group.ghost.location
  resource_group_name = azurerm_resource_group.ghost.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  # Enable RBAC for access control
  enable_rbac_authorization = true

  # Security settings
  purge_protection_enabled   = false  # Set to true for production
  soft_delete_retention_days = 7

  network_acls {
    default_action = "Allow"  # Restrict for production
    bypass         = "AzureServices"
  }

  tags = var.common_tags
}

# Key Vault access policy for current user/service principal
resource "azurerm_role_assignment" "kv_admin" {
  scope                = azurerm_key_vault.ghost.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Key Vault access policy for Container Apps
resource "azurerm_role_assignment" "kv_secrets_user" {
  scope                = azurerm_key_vault.ghost.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.ghost.principal_id
}

# Generate random password for MySQL
resource "random_password" "mysql_password" {
  length  = 32
  special = true
}

# Store MySQL password in Key Vault
resource "azurerm_key_vault_secret" "mysql_password" {
  name         = "mysql-password"
  value        = random_password.mysql_password.result
  key_vault_id = azurerm_key_vault.ghost.id

  depends_on = [azurerm_role_assignment.kv_admin]

  tags = var.common_tags
}

# Store Cloudflare API token in Key Vault
resource "azurerm_key_vault_secret" "cloudflare_token" {
  name         = "cloudflare-api-token"
  value        = var.cloudflare_api_token
  key_vault_id = azurerm_key_vault.ghost.id

  depends_on = [azurerm_role_assignment.kv_admin]

  tags = var.common_tags
}
