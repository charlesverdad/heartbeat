# MySQL Flexible Server
resource "azurerm_mysql_flexible_server" "ghost" {
  name                   = "${var.project_name}-${var.environment}-mysql"
  resource_group_name    = azurerm_resource_group.ghost.name
  location               = azurerm_resource_group.ghost.location
  administrator_login    = var.mysql_admin_username
  administrator_password = random_password.mysql_password.result

  # Server configuration
  sku_name   = "B_Standard_B1s"  # Burstable tier for cost optimization
  version    = "8.0.21"
  
  # Storage configuration
  storage {
    size_gb = 20
    iops    = 360
  }

  # Backup configuration
  backup_retention_days        = 7
  geo_redundant_backup_enabled = false

  # High availability (disabled for cost optimization)
  high_availability {
    mode = "Disabled"
  }

  tags = var.common_tags
}

# Database for Ghost
resource "azurerm_mysql_flexible_database" "ghost" {
  name                = "ghost"
  resource_group_name = azurerm_resource_group.ghost.name
  server_name         = azurerm_mysql_flexible_server.ghost.name
  charset             = "utf8mb4"
  collation           = "utf8mb4_unicode_ci"
}

# Firewall rule to allow Azure services
resource "azurerm_mysql_flexible_server_firewall_rule" "azure_services" {
  name             = "AllowAzureServices"
  resource_group_name = azurerm_resource_group.ghost.name
  server_name      = azurerm_mysql_flexible_server.ghost.name
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Configuration for MySQL
resource "azurerm_mysql_flexible_server_configuration" "ghost_configs" {
  for_each = {
    "innodb_buffer_pool_size" = "134217728"  # 128MB
    "max_connections"         = "100"
    "wait_timeout"           = "28800"
  }

  name                = each.key
  resource_group_name = azurerm_resource_group.ghost.name
  server_name         = azurerm_mysql_flexible_server.ghost.name
  value               = each.value
}
