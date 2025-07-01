# Log Analytics Workspace for AKS monitoring
resource "azurerm_log_analytics_workspace" "aks" {
  name                = "log-${var.project_name}-aks-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  sku                 = "PerGB2018"
  retention_in_days   = 30 # Minimal retention for cost optimization
  tags                = var.tags
}

# Application Insights for application monitoring (optional)
resource "azurerm_application_insights" "aks" {
  name                = "appi-${var.project_name}-aks-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  workspace_id        = azurerm_log_analytics_workspace.aks.id
  application_type    = "web"
  tags                = var.tags
}
