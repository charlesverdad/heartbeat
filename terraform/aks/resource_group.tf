resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

resource "azurerm_resource_group" "aks" {
  name     = "rg-${var.project_name}-aks-${var.environment}-${random_string.suffix.result}"
  location = var.location
  tags     = var.tags
}
