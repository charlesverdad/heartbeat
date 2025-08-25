output "vm_private_ip" {
  description = "Private IP address of the VM"
  value       = azurerm_network_interface.vm.private_ip_address
}

output "vm_name" {
  description = "Name of the virtual machine"
  value       = azurerm_linux_virtual_machine.vm.name
}

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.vm.name
}

output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.vm.name
}

output "managed_identity_principal_id" {
  description = "Principal ID of the managed identity"
  value       = azurerm_user_assigned_identity.vm.principal_id
}

output "managed_identity_client_id" {
  description = "Client ID of the managed identity"
  value       = azurerm_user_assigned_identity.vm.client_id
}

output "vnet_name" {
  description = "Name of the virtual network"
  value       = azurerm_virtual_network.vm.name
}

output "subnet_name" {
  description = "Name of the subnet"
  value       = azurerm_subnet.vm.name
}
