terraform {
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state-backend"
    storage_account_name = "terraforminfratfstate"
    container_name       = "tfstate"
    key                  = "acr/terraform.tfstate"
    use_azuread_auth     = true
  }
}
