# Get current user information
data "azuread_client_config" "current" {}

# Create Azure AD group for AKS administrators
resource "azuread_group" "aks_admins" {
  display_name     = "${var.project_name}-aks-admins-${var.environment}"
  description      = "Administrators for ${var.project_name} AKS cluster in ${var.environment} environment"
  security_enabled = true

  # Add current user as owner and member of the group
  owners = [data.azuread_client_config.current.object_id]
  members = [data.azuread_client_config.current.object_id]
}
