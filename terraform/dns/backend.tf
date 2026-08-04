terraform {
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state-backend"
    storage_account_name = "terraforminfratfstate"
    container_name       = "tfstate"
    # key is supplied at init time by bin/tf.py as <dir>/<flavor>.tfstate
    use_azuread_auth = true
  }
}
