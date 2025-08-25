terraform {
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state-backend"
    storage_account_name = "terraforminfratfstate"
    container_name       = "tfstate"
    use_azuread_auth     = true
    # key will be specified during terraform init
  }
}
