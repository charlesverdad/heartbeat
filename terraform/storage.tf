# Random suffix for storage account name (must be globally unique)
resource "random_string" "storage_suffix" {
  length  = 8
  special = false
  upper   = false
}

# Storage Account for Ghost uploads and content
resource "azurerm_storage_account" "ghost" {
  name                     = "${var.project_name}${var.environment}st${random_string.storage_suffix.result}"
  resource_group_name      = azurerm_resource_group.ghost.name
  location                 = azurerm_resource_group.ghost.location
  account_tier             = "Standard"
  account_replication_type = "LRS"  # Use GRS for production
  account_kind             = "StorageV2"

  # Security settings
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  
  # Blob properties
  blob_properties {
    cors_rule {
      allowed_headers    = ["*"]
      allowed_methods    = ["GET", "HEAD", "POST", "PUT"]
      allowed_origins    = ["https://${var.subdomain}.${var.domain_name}"]
      exposed_headers    = ["*"]
      max_age_in_seconds = 3600
    }
    
    delete_retention_policy {
      days = 7
    }
    
    versioning_enabled = true
  }

  tags = var.common_tags
}

# Container for Ghost uploads
resource "azurerm_storage_container" "ghost_uploads" {
  name                  = "uploads"
  storage_account_name  = azurerm_storage_account.ghost.name
  container_access_type = "blob"  # Public read access for uploaded files
}

# Container for Ghost themes
resource "azurerm_storage_container" "ghost_themes" {
  name                  = "themes"
  storage_account_name  = azurerm_storage_account.ghost.name
  container_access_type = "private"
}

# Container for Ghost content
resource "azurerm_storage_container" "ghost_content" {
  name                  = "content"
  storage_account_name  = azurerm_storage_account.ghost.name
  container_access_type = "private"
}

# Store storage account connection string in Key Vault
resource "azurerm_key_vault_secret" "storage_connection_string" {
  name         = "storage-connection-string"
  value        = azurerm_storage_account.ghost.primary_connection_string
  key_vault_id = azurerm_key_vault.ghost.id

  depends_on = [azurerm_role_assignment.kv_admin]

  tags = var.common_tags
}

# Store storage account access key in Key Vault
resource "azurerm_key_vault_secret" "storage_access_key" {
  name         = "storage-access-key"
  value        = azurerm_storage_account.ghost.primary_access_key
  key_vault_id = azurerm_key_vault.ghost.id

  depends_on = [azurerm_role_assignment.kv_admin]

  tags = var.common_tags
}
