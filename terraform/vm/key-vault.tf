# Get current client configuration
data "azurerm_client_config" "current" {}

# Key Vault
resource "azurerm_key_vault" "vm" {
  name                        = "kv-${var.vm_name}-${var.environment}-${random_string.suffix.result}"
  location                    = azurerm_resource_group.vm.location
  resource_group_name         = azurerm_resource_group.vm.name
  enabled_for_disk_encryption = true
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false
  sku_name                    = "standard"

  # Allow current user (terraform) to manage secrets
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = [
      "Get",
      "List",
      "Set",
      "Delete",
      "Recover",
      "Backup",
      "Restore"
    ]
  }

  # Allow VM managed identity to read secrets
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = azurerm_user_assigned_identity.vm.principal_id

    secret_permissions = [
      "Get",
      "List"
    ]
  }

  tags = var.tags
}

# Cloudflare tunnel token (automatically generated)
resource "azurerm_key_vault_secret" "cloudflare_tunnel_token" {
  name         = "cloudflare-tunnel-token"
  value        = cloudflare_zero_trust_tunnel_cloudflared.vm_ssh.tunnel_token
  key_vault_id = azurerm_key_vault.vm.id
}

resource "azurerm_key_vault_secret" "cloudflare_ca_public_key" {
  name         = "cloudflare-ca-public-key"
  value        = "PLACEHOLDER_CA_PUBLIC_KEY_CHANGE_AFTER_DEPLOYMENT"
  key_vault_id = azurerm_key_vault.vm.id

  lifecycle {
    ignore_changes = [value]
  }
}

resource "azurerm_key_vault_secret" "git_repo_url" {
  name         = "git-repo-url"
  value        = var.git_repo_url
  key_vault_id = azurerm_key_vault.vm.id
}
