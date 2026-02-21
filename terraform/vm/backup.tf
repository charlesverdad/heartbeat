# Backup vault for data disk snapshots
resource "azurerm_data_protection_backup_vault" "vm" {
  name                = "bvault-${var.vm_name}-${var.environment}-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.vm.name
  location            = azurerm_resource_group.vm.location
  datastore_type      = "VaultStore"
  redundancy          = "LocallyRedundant"

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# The backup vault identity needs "Disk Snapshot Contributor" on the resource group
# to create snapshots
resource "azurerm_role_assignment" "backup_snapshot_contributor" {
  scope                = azurerm_resource_group.vm.id
  role_definition_name = "Disk Snapshot Contributor"
  principal_id         = azurerm_data_protection_backup_vault.vm.identity[0].principal_id
}

# The backup vault identity needs "Disk Backup Reader" on the managed disk
resource "azurerm_role_assignment" "backup_disk_reader" {
  scope                = azurerm_managed_disk.vm_data.id
  role_definition_name = "Disk Backup Reader"
  principal_id         = azurerm_data_protection_backup_vault.vm.identity[0].principal_id
}

# Daily backup policy with 60-day retention
resource "azurerm_data_protection_backup_policy_disk" "daily" {
  name     = "policy-daily-60d"
  vault_id = azurerm_data_protection_backup_vault.vm.id

  # Daily at 2:00 AM AEST (16:00 UTC previous day)
  backup_repeating_time_intervals = ["R/2024-01-01T16:00:00+00:00/P1D"]
  default_retention_duration      = "P60D"
}

# Backup instance for the data disk
resource "azurerm_data_protection_backup_instance_disk" "vm_data" {
  name                         = "backup-${var.vm_name}-${var.environment}-data"
  location                     = azurerm_data_protection_backup_vault.vm.location
  vault_id                     = azurerm_data_protection_backup_vault.vm.id
  disk_id                      = azurerm_managed_disk.vm_data.id
  snapshot_resource_group_name = azurerm_resource_group.vm.name
  backup_policy_id             = azurerm_data_protection_backup_policy_disk.daily.id

  depends_on = [
    azurerm_role_assignment.backup_snapshot_contributor,
    azurerm_role_assignment.backup_disk_reader,
  ]
}
