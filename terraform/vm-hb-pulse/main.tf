# Data sources
data "azurerm_client_config" "current" {}

# Random string for naming
resource "random_string" "suffix" {
  length  = 4
  special = false
  upper   = false
}

# Reference the existing VM's resource group and managed identity
data "azurerm_resource_group" "vm" {
  name = var.vm_resource_group_name
}

data "azurerm_user_assigned_identity" "vm" {
  name                = var.vm_managed_identity_name
  resource_group_name = data.azurerm_resource_group.vm.name
}

# Azure Key Vault for storing secrets
resource "azurerm_key_vault" "pulse" {
  name                = "kv-${var.project_name}-${var.environment}-${random_string.suffix.result}"
  location            = data.azurerm_resource_group.vm.location
  resource_group_name = data.azurerm_resource_group.vm.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  # Enable RBAC authorization instead of access policies
  enable_rbac_authorization = true

  soft_delete_retention_days = 7
  purge_protection_enabled   = false

  network_acls {
    default_action = "Allow"
    bypass         = "AzureServices"
  }

  tags = var.tags
}

# Role assignment to allow the VM's identity to access Key Vault secrets
resource "azurerm_role_assignment" "vm_keyvault_secrets_user" {
  scope                = azurerm_key_vault.pulse.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = data.azurerm_user_assigned_identity.vm.principal_id
}

# Role assignment for current user to manage secrets during deployment
resource "azurerm_role_assignment" "current_user_keyvault_admin" {
  scope                = azurerm_key_vault.pulse.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# ── Key Vault Secrets ────────────────────────────────────────────────────────

resource "azurerm_key_vault_secret" "session_secret" {
  name         = "session-secret"
  value        = var.session_secret
  key_vault_id = azurerm_key_vault.pulse.id

  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

resource "azurerm_key_vault_secret" "db_password" {
  name         = "db-password"
  value        = var.db_password
  key_vault_id = azurerm_key_vault.pulse.id

  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

resource "azurerm_key_vault_secret" "google_client_id" {
  name         = "google-client-id"
  value        = var.google_client_id
  key_vault_id = azurerm_key_vault.pulse.id

  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

resource "azurerm_key_vault_secret" "google_client_secret" {
  name         = "google-client-secret"
  value        = var.google_client_secret
  key_vault_id = azurerm_key_vault.pulse.id

  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

resource "azurerm_key_vault_secret" "vapid_public_key" {
  name         = "vapid-public-key"
  value        = var.vapid_public_key
  key_vault_id = azurerm_key_vault.pulse.id

  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

resource "azurerm_key_vault_secret" "vapid_private_key" {
  name         = "vapid-private-key"
  value        = var.vapid_private_key
  key_vault_id = azurerm_key_vault.pulse.id

  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

resource "azurerm_key_vault_secret" "smtp_pass" {
  name         = "smtp-pass"
  value        = var.smtp_pass
  key_vault_id = azurerm_key_vault.pulse.id

  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

resource "azurerm_key_vault_secret" "cloudflare_tunnel_token" {
  name         = "cloudflare-tunnel-token"
  value        = cloudflare_zero_trust_tunnel_cloudflared.pulse.tunnel_token
  key_vault_id = azurerm_key_vault.pulse.id

  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

# ── Cloudflare Tunnel ────────────────────────────────────────────────────────

# Random secret for Cloudflare tunnel
resource "random_string" "tunnel_secret" {
  length  = 64
  special = false
}

# Create a tunnel that will connect to the Pulse container
resource "cloudflare_zero_trust_tunnel_cloudflared" "pulse" {
  account_id = var.cloudflare_account_id
  name       = "${var.project_name}-${var.environment}-tunnel"
  secret     = base64encode(random_string.tunnel_secret.result)
}

# DNS record pointing to the tunnel
resource "cloudflare_record" "pulse" {
  zone_id = var.cloudflare_zone_id
  name    = replace(var.domain_name, ".heartbeatchurch.com.au", "")
  content = cloudflare_zero_trust_tunnel_cloudflared.pulse.cname
  type    = "CNAME"
  proxied = true
  ttl     = 1
  comment = "Managed by Terraform - points to Cloudflare tunnel for ${var.project_name}-${var.environment}"
}

# Tunnel configuration to route traffic to Pulse app (port 3001 on host)
resource "cloudflare_zero_trust_tunnel_cloudflared_config" "pulse" {
  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.pulse.id

  config {
    ingress_rule {
      hostname = var.domain_name
      service  = "http://localhost:3001"

      origin_request {
        http_host_header = var.domain_name
      }
    }

    # Catch-all rule (required)
    ingress_rule {
      service = "http_status:404"
    }
  }
}
