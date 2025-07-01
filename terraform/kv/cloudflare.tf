terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Get current Azure client configuration
data "azurerm_client_config" "current" {}

# Create Resource Group for Terraform Key Vault
resource "azurerm_resource_group" "terraform_kv" {
  name     = "rg-terraform-keyvault-${var.environment}"
  location = var.location

  tags = {
    Project     = "Terraform"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "Secret storage for Terraform operations"
  }
}

# Create Key Vault for Terraform secrets
resource "azurerm_key_vault" "terraform" {
  name                = "kv-terraform-${var.environment}"
  location            = azurerm_resource_group.terraform_kv.location
  resource_group_name = azurerm_resource_group.terraform_kv.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  # Soft delete configuration - important for production
  soft_delete_retention_days = 90
  purge_protection_enabled   = true

  # Enable public network access (adjust as needed for your security requirements)
  public_network_access_enabled = true

  # Simple access policy for current user
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = [
      "Get",
      "List",
      "Set",
      "Delete",
      "Recover",
      "Purge"
    ]
  }

  tags = {
    Project     = "Terraform"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "Secret storage for Terraform operations"
  }
}

# This token is used to create cloudflare resources via Terraform
resource "azurerm_key_vault_secret" "cloudflare_api_token" {
  name         = "tf-cloudflare-api-token"
  value        = "replace-me-with-actual-token"
  key_vault_id = azurerm_key_vault.terraform.id
}

# Outputs
output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.terraform.name
}
