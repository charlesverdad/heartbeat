# Data sources
data "azurerm_client_config" "current" {}

# Random string for naming
resource "random_string" "suffix" {
  length  = 4
  special = false
  upper   = false
}

# Resource group for website infrastructure
resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project_name}-${var.environment}-${random_string.suffix.result}"
  location = var.location
  tags     = var.tags
}

# Azure Key Vault for storing secrets
resource "azurerm_key_vault" "main" {
  name                = "kv-${var.project_name}-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  soft_delete_retention_days = 7
  purge_protection_enabled   = false

  network_acls {
    default_action = "Allow"
    bypass         = "AzureServices"
  }

  tags = var.tags
}

# User-Assigned Managed Identity for the application
resource "azurerm_user_assigned_identity" "main" {
  name                = "id-${var.project_name}-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

# Role assignment to allow the identity to access Key Vault secrets
resource "azurerm_role_assignment" "keyvault_secrets_user" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.main.principal_id
}

# Role assignment for AKS kubelet to use this identity (reference from AKS module)
resource "azurerm_role_assignment" "aks_identity_operator" {
  scope                = azurerm_user_assigned_identity.main.id
  role_definition_name = "Managed Identity Operator"
  principal_id         = var.aks_kubelet_identity_object_id
}
