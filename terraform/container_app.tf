# User-assigned identity for Container App
resource "azurerm_user_assigned_identity" "ghost" {
  name                = "${var.project_name}-${var.environment}-identity"
  location            = azurerm_resource_group.ghost.location
  resource_group_name = azurerm_resource_group.ghost.name

  tags = var.common_tags
}

# Container Apps Environment
resource "azurerm_container_app_environment" "ghost" {
  name                       = "${var.project_name}-${var.environment}-env"
  location                   = azurerm_resource_group.ghost.location
  resource_group_name        = azurerm_resource_group.ghost.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.ghost.id

  tags = var.common_tags
}

# Log Analytics Workspace for Container Apps
resource "azurerm_log_analytics_workspace" "ghost" {
  name                = "${var.project_name}-${var.environment}-logs"
  location            = azurerm_resource_group.ghost.location
  resource_group_name = azurerm_resource_group.ghost.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = var.common_tags
}

# Azure Container App for Ghost
resource "azurerm_container_app" "ghost" {
  name                         = "${var.project_name}-${var.environment}-app"
  container_app_environment_id = azurerm_container_app_environment.ghost.id
  resource_group_name          = azurerm_resource_group.ghost.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.ghost.id]
  }

  template {
    container {
      name   = "ghost"
      image  = "ghost:latest"
      cpu    = var.container_cpu
      memory = var.container_memory

      env {
        name  = "url"
        value = "https://${var.subdomain}.${var.domain_name}"
      }

      env {
        name  = "database__client"
        value = "mysql"
      }

      env {
        name  = "database__connection__host"
        value = azurerm_mysql_flexible_server.ghost.fqdn
      }

      env {
        name  = "database__connection__user"
        value = var.mysql_admin_username
      }

      env {
        name  = "database__connection__database"
        value = azurerm_mysql_flexible_database.ghost.name
      }

      env {
        name        = "database__connection__password"
        secret_name = "mysql-password"
      }

      env {
        name        = "AZURE_STORAGE_CONNECTION_STRING"
        secret_name = "storage-connection-string"
      }
    }

    min_replicas = var.min_replicas
    max_replicas = var.max_replicas
  }

  secret {
    name  = "mysql-password"
    value = random_password.mysql_password.result
  }

  secret {
    name  = "storage-connection-string"
    value = azurerm_storage_account.ghost.primary_connection_string
  }

  ingress {
    external_enabled = true
    target_port      = 2368

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = var.common_tags
}
