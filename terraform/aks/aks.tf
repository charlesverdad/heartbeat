# AKS Cluster
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "${var.project_name}-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  dns_prefix          = "${var.project_name}-${var.environment}-${random_string.suffix.result}"
  kubernetes_version  = var.kubernetes_version

  # Enable private cluster for security
  private_cluster_enabled = var.private_cluster_enabled

  # Network configuration
  network_profile {
    network_plugin    = "azure"
    network_policy    = "azure"
    load_balancer_sku = "standard"
  }

  # Default node pool
  default_node_pool {
    name               = "default"
    node_count         = var.node_count
    vm_size            = var.node_vm_size
    enable_auto_scaling = true
    min_count          = 1
    max_count          = 5
    max_pods           = 30
    os_disk_size_gb    = 30
    vnet_subnet_id     = azurerm_subnet.aks_nodes.id
  }


  # Identity configuration using managed identity
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks.id]
  }

  # Kubelet identity
  kubelet_identity {
    client_id                 = azurerm_user_assigned_identity.kubelet.client_id
    object_id                 = azurerm_user_assigned_identity.kubelet.principal_id
    user_assigned_identity_id = azurerm_user_assigned_identity.kubelet.id
  }

  # Azure AD integration for RBAC
  azure_active_directory_role_based_access_control {
    managed                = true
    admin_group_object_ids = [azuread_group.aks_admins.object_id]
    azure_rbac_enabled     = true
  }

  # Security features
  role_based_access_control_enabled = true
  
  # OIDC Issuer for Workload Identity
  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  # Add-ons
  azure_policy_enabled = true

  # Monitoring
  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.aks.id
  }


  tags = var.tags

  depends_on = [
    azurerm_role_assignment.aks_cluster_contributor,
    azurerm_role_assignment.aks_network_contributor,
  ]
}
