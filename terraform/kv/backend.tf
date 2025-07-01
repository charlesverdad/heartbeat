# Backend configuration for terraform environment
# TODO: Configure remote state storage once storage account is created
# 
# For now using local state. To migrate to remote state later:
# 
# 1. Create storage account for terraform state
# 2. Uncomment and configure the backend block below
# 3. Run: terraform init -migrate-state
#
# terraform {
#   backend "azurerm" {
#     storage_account_name = "your-terraform-state-storage"
#     container_name       = "tfstate"
#     key                  = "terraform.tfstate"
#     resource_group_name  = "rg-terraform-state"
#   }
# }
