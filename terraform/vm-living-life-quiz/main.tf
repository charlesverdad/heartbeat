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
resource "azurerm_key_vault" "living_life_quiz" {
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
  scope                = azurerm_key_vault.living_life_quiz.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = data.azurerm_user_assigned_identity.vm.principal_id
}

# Role assignment for current user to manage secrets during deployment
resource "azurerm_role_assignment" "current_user_keyvault_admin" {
  scope                = azurerm_key_vault.living_life_quiz.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Store application secrets in Key Vault
resource "azurerm_key_vault_secret" "teacher_password" {
  name         = "teacher-password"
  value        = var.teacher_password
  key_vault_id = azurerm_key_vault.living_life_quiz.id
  
  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

resource "azurerm_key_vault_secret" "session_secret" {
  name         = "session-secret"
  value        = var.session_secret
  key_vault_id = azurerm_key_vault.living_life_quiz.id
  
  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

# Cloudflare Tunnel Resources
# Create a tunnel that will connect to the quiz container
resource "cloudflare_zero_trust_tunnel_cloudflared" "living_life_quiz" {
  account_id = var.cloudflare_account_id
  name       = "${var.project_name}-${var.environment}-tunnel"
  secret     = base64encode(random_string.tunnel_secret.result)
}

# Random secret for Cloudflare tunnel
resource "random_string" "tunnel_secret" {
  length  = 64
  special = false
}

# Store Cloudflare tunnel token in Key Vault
resource "azurerm_key_vault_secret" "cloudflare_tunnel_token" {
  name         = "cloudflare-tunnel-token"
  value        = cloudflare_zero_trust_tunnel_cloudflared.living_life_quiz.tunnel_token
  key_vault_id = azurerm_key_vault.living_life_quiz.id
  
  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

# DNS record pointing to the tunnel
resource "cloudflare_record" "living_life_quiz" {
  zone_id = var.cloudflare_zone_id
  name    = replace(var.domain_name, ".heartbeatchurch.com.au", "")
  content = cloudflare_zero_trust_tunnel_cloudflared.living_life_quiz.cname
  type    = "CNAME"
  proxied = true
  ttl     = 1
  comment = "Managed by Terraform - points to Cloudflare tunnel for ${var.project_name}-${var.environment}"
}

# Tunnel configuration to route traffic to quiz app
resource "cloudflare_zero_trust_tunnel_cloudflared_config" "living_life_quiz" {
  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.living_life_quiz.id

  config {
    ingress_rule {
      hostname = var.domain_name
      service  = "http://localhost:3000"
      
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
