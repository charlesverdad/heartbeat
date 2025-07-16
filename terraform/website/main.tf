# Data sources
data "azurerm_client_config" "current" {}

# Data source for AKS remote state
data "terraform_remote_state" "aks" {
  backend = "local"
  config = {
    path = "../aks/dev.tfstate"
  }
}

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

# Role assignment for current user to manage secrets during deployment
resource "azurerm_role_assignment" "current_user_keyvault_admin" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Role assignment for AKS kubelet to use this identity (reference from AKS module)
resource "azurerm_role_assignment" "aks_identity_operator" {
  scope                = azurerm_user_assigned_identity.main.id
  role_definition_name = "Managed Identity Operator"
  principal_id         = var.aks_kubelet_identity_object_id
}

# Federated identity credential for Azure Workload Identity
resource "azurerm_federated_identity_credential" "website_workload_identity" {
  name                = "website-workload-identity"
  resource_group_name = azurerm_resource_group.main.name
  audience            = ["api://AzureADTokenExchange"]
  issuer              = data.terraform_remote_state.aks.outputs.oidc_issuer_url
  parent_id           = azurerm_user_assigned_identity.main.id
  subject             = "system:serviceaccount:website-dev:website-sa"
}

# Generate random password for MySQL
resource "random_password" "mysql_admin" {
  length  = 16
  special = true
}

# Azure Database for MySQL - Flexible Server (cost-effective)
resource "azurerm_mysql_flexible_server" "main" {
  name                   = "mysql-${var.project_name}-${var.environment}-${random_string.suffix.result}"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  
  # Minimal configuration for cost savings
  administrator_login    = "ghostadmin"
  administrator_password = random_password.mysql_admin.result
  
  # Cheapest tier available
  sku_name = "B_Standard_B1ms"  # Burstable, 1 vCore, 2GB RAM
  
  # Minimal storage (20GB minimum)
  storage {
    size_gb = 20
    iops    = 360  # Minimum for this tier
  }
  
  # MySQL version
  version = "8.0.21"
  
  # Availability zone (set to match existing)
  zone = "1"
  
  # Backup configuration - weekly to save costs
  backup_retention_days = 7
  
  # High availability disabled for cost savings (omit the block to disable)
  # high_availability {
  #   mode = "ZoneRedundant"  # Only ZoneRedundant or SameZone allowed
  # }
  
  # Network access is determined automatically
  
  tags = var.tags
}

# Firewall rule to allow Azure services
resource "azurerm_mysql_flexible_server_firewall_rule" "allow_azure_services" {
  name                = "AllowAzureServices"
  resource_group_name = azurerm_resource_group.main.name
  server_name         = azurerm_mysql_flexible_server.main.name
  start_ip_address    = "0.0.0.0"
  end_ip_address      = "0.0.0.0"
}

# Create Ghost database
resource "azurerm_mysql_flexible_database" "ghost" {
  name                = "ghost"
  resource_group_name = azurerm_resource_group.main.name
  server_name         = azurerm_mysql_flexible_server.main.name
  charset             = "utf8mb4"
  collation           = "utf8mb4_unicode_ci"
}

# Store MySQL connection details in Key Vault
resource "azurerm_key_vault_secret" "mysql_connection_string" {
  name         = "mysql-connection-string"
  value        = "mysql://${azurerm_mysql_flexible_server.main.administrator_login}:${random_password.mysql_admin.result}@${azurerm_mysql_flexible_server.main.fqdn}:3306/${azurerm_mysql_flexible_database.ghost.name}?ssl=true"
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_role_assignment.keyvault_secrets_user
  ]
}

resource "azurerm_key_vault_secret" "mysql_password" {
  name         = "mysql-password"
  value        = random_password.mysql_admin.result
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_role_assignment.keyvault_secrets_user
  ]
}

resource "azurerm_key_vault_secret" "mysql_host" {
  name         = "mysql-host"
  value        = azurerm_mysql_flexible_server.main.fqdn
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_role_assignment.keyvault_secrets_user
  ]
}

# Store Cloudflare tunnel token in Key Vault (placeholder for now)
resource "azurerm_key_vault_secret" "cloudflare_tunnel_token" {
  name         = "cloudflare-tunnel-token"
  value        = "placeholder-token-replace-with-actual-cloudflare-tunnel-token"
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_role_assignment.keyvault_secrets_user
  ]
}
