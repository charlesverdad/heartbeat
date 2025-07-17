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

# User-Assigned Managed Identity for the Container App
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

# Storage account for Azure Files
resource "azurerm_storage_account" "main" {
  name                     = "st${replace(var.project_name, "-", "")}${var.environment}${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  
  tags = var.tags
}

# Azure Files share for Ghost content
resource "azurerm_storage_share" "ghost_content" {
  name                 = "ghost-content"
  storage_account_name = azurerm_storage_account.main.name
  quota                = 20
}

# Container Apps Environment
resource "azurerm_container_app_environment" "main" {
  name                = "cae-${var.project_name}-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
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
  administrator_login    = var.mysql_admin_username
  administrator_password = random_password.mysql_admin.result
  
  # Cheapest tier available
  sku_name = "B_Standard_B1ms"  # Burstable, 1 vCore, 2GB RAM
  
  # Minimal storage (20GB minimum)
  storage {
    size_gb = 20
    iops    = 360  # Minimum for this tier
  }
  
  # MySQL version
  version = var.mysql_version
  
  # Availability zone
  zone = var.mysql_availability_zone
  
  # Backup configuration - weekly to save costs
  backup_retention_days = 7
  
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
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

resource "azurerm_key_vault_secret" "mysql_password" {
  name         = "mysql-password"
  value        = random_password.mysql_admin.result
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

resource "azurerm_key_vault_secret" "mysql_host" {
  name         = "mysql-host"
  value        = azurerm_mysql_flexible_server.main.fqdn
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

# Store Gmail app password in Key Vault
resource "azurerm_key_vault_secret" "gmail_app_password" {
  name         = "gmail-app-password"
  value        = "placeholder-gmail-app-password-replace-with-actual-value"
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
  
  lifecycle {
    ignore_changes = [value]
  }
}

# Cloudflare Tunnel Resources
# Create a tunnel that will connect to the Ghost container app
resource "cloudflare_zero_trust_tunnel_cloudflared" "website" {
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
  value        = cloudflare_zero_trust_tunnel_cloudflared.website.tunnel_token
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

# DNS record pointing to the tunnel
resource "cloudflare_record" "website" {
  zone_id = var.cloudflare_zone_id
  name    = replace(var.domain_name, ".heartbeatchurch.com.au", "")
  value   = cloudflare_zero_trust_tunnel_cloudflared.website.cname
  type    = "CNAME"
  proxied = true
  ttl     = 1
  comment = "Managed by Terraform - points to Cloudflare tunnel for ${var.project_name}-${var.environment}"
}

# Tunnel configuration to route traffic to Ghost app
resource "cloudflare_zero_trust_tunnel_cloudflared_config" "website" {
  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.website.id

  config {
    ingress_rule {
      hostname = var.domain_name
      service  = "http://${azurerm_container_app.ghost.ingress[0].fqdn}"
      
      origin_request {
        connect_timeout          = "30s"
        tls_timeout             = "10s"
        tcp_keep_alive          = "30s"
        no_happy_eyeballs       = false
        keep_alive_connections  = 1024
        keep_alive_timeout      = "1m30s"
        http_host_header        = var.domain_name
      }
    }
    
    # Catch-all rule (required)
    ingress_rule {
      service = "http_status:404"
    }
  }
}

# Container App for Ghost
resource "azurerm_container_app" "ghost" {
  name                         = "ca-ghost-${var.environment}-${random_string.suffix.result}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.main.id]
  }

  template {
    min_replicas = 1
    max_replicas = 1

    volume {
      name         = "ghost-content"
      storage_type = "AzureFile"
      storage_name = azurerm_container_app_environment_storage.ghost_content.name
    }

    container {
      name   = "ghost"
      image  = "ghost:5.96.0-alpine"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "NODE_ENV"
        value = "production"
      }

      env {
        name  = "url"
        value = "https://${var.domain_name}"
      }

      env {
        name  = "database__client"
        value = "mysql"
      }

      env {
        name  = "database__connection__user"
        value = var.mysql_admin_username
      }

      env {
        name  = "database__connection__database"
        value = "ghost"
      }

      env {
        name        = "database__connection__password"
        secret_name = "mysql-password"
      }

      env {
        name        = "database__connection__host"
        secret_name = "mysql-host"
      }

      env {
        name  = "database__connection__ssl__rejectUnauthorized"
        value = "false"
      }

      env {
        name  = "mail__transport"
        value = "SMTP"
      }

      env {
        name  = "mail__from"
        value = "hello@heartbeatchurch.com.au"
      }

      env {
        name  = "mail__options__host"
        value = "smtp.gmail.com"
      }

      env {
        name  = "mail__options__port"
        value = "465"
      }

      env {
        name  = "mail__options__secure"
        value = "true"
      }

      env {
        name  = "mail__options__auth__user"
        value = "hello@heartbeatchurch.com.au"
      }

      env {
        name        = "mail__options__auth__pass"
        secret_name = "gmail-app-password"
      }

      volume_mounts {
        name = "ghost-content"
        path = "/var/lib/ghost/content"
      }
    }
  }

  secret {
    name                = "gmail-app-password"
    key_vault_secret_id = azurerm_key_vault_secret.gmail_app_password.id
    identity            = azurerm_user_assigned_identity.main.id
  }

  secret {
    name                = "mysql-password"
    key_vault_secret_id = azurerm_key_vault_secret.mysql_password.id
    identity            = azurerm_user_assigned_identity.main.id
  }

  secret {
    name                = "mysql-host"
    key_vault_secret_id = azurerm_key_vault_secret.mysql_host.id
    identity            = azurerm_user_assigned_identity.main.id
  }

  ingress {
    external_enabled = false  # Only accessible within the container app environment
    target_port      = 2368

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  depends_on = [
    azurerm_role_assignment.keyvault_secrets_user,
    azurerm_container_app_environment_storage.ghost_content
  ]

  tags = var.tags
}

# Container App Environment Storage for Azure Files
resource "azurerm_container_app_environment_storage" "ghost_content" {
  name                         = "ghost-content-storage"
  container_app_environment_id = azurerm_container_app_environment.main.id
  account_name                 = azurerm_storage_account.main.name
  share_name                   = azurerm_storage_share.ghost_content.name
  access_key                   = azurerm_storage_account.main.primary_access_key
  access_mode                  = "ReadWrite"
}

# Container App for Cloudflare Tunnel
resource "azurerm_container_app" "cloudflare_tunnel" {
  name                         = "ca-tunnel-${var.environment}-${random_string.suffix.result}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.main.id]
  }
  
  template {
    min_replicas = 1
    max_replicas = 1
    
    container {
      name   = "cloudflared"
      image  = "cloudflare/cloudflared:latest"
      cpu    = 0.25
      memory = "0.5Gi"
      
      args = [
        "tunnel",
        "run",
        "--token",
        "$(TUNNEL_TOKEN)"
      ]
      
      env {
        name        = "TUNNEL_TOKEN"
        secret_name = "cloudflare-tunnel-token"
      }
    }
  }
  
  secret {
    name                = "cloudflare-tunnel-token"
    key_vault_secret_id = azurerm_key_vault_secret.cloudflare_tunnel_token.id
    identity            = azurerm_user_assigned_identity.main.id
  }
  
  # No ingress needed - this is an outbound tunnel connector
  
  depends_on = [
    azurerm_role_assignment.keyvault_secrets_user,
    cloudflare_zero_trust_tunnel_cloudflared_config.website
  ]
  
  tags = var.tags
}
