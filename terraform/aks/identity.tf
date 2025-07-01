# User-assigned managed identity for AKS cluster
resource "azurerm_user_assigned_identity" "aks" {
  name                = "id-${var.project_name}-aks-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  tags                = var.tags
}

# User-assigned managed identity for kubelet (node identity)
resource "azurerm_user_assigned_identity" "kubelet" {
  name                = "id-${var.project_name}-kubelet-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  tags                = var.tags
}

# Role assignment for AKS cluster identity to manage the resource group
resource "azurerm_role_assignment" "aks_cluster_contributor" {
  scope                = azurerm_resource_group.aks.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.aks.principal_id
}

# Role assignment for AKS cluster identity to manage network resources
resource "azurerm_role_assignment" "aks_network_contributor" {
  scope                = azurerm_virtual_network.aks.id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_user_assigned_identity.aks.principal_id
}

# Role assignment for kubelet identity to pull images from ACR (if needed)
resource "azurerm_role_assignment" "kubelet_acr_pull" {
  scope                = azurerm_resource_group.aks.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.kubelet.principal_id
}
