# Random string for unique resource naming
resource "random_string" "suffix" {
  length  = 4
  special = false
  upper   = false
}

# Resource group
resource "azurerm_resource_group" "vm" {
  name     = "rg-${var.vm_name}-${var.environment}-${random_string.suffix.result}"
  location = var.location
  tags     = var.tags
}

# User-assigned managed identity
resource "azurerm_user_assigned_identity" "vm" {
  name                = "id-${var.vm_name}-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.vm.location
  resource_group_name = azurerm_resource_group.vm.name
  tags                = var.tags
}

# Virtual network
resource "azurerm_virtual_network" "vm" {
  name                = "vnet-${var.vm_name}-${var.environment}"
  address_space       = [var.vnet_address_space]
  location            = azurerm_resource_group.vm.location
  resource_group_name = azurerm_resource_group.vm.name
  tags                = var.tags
}

# Subnet
resource "azurerm_subnet" "vm" {
  name                 = "snet-${var.vm_name}-${var.environment}"
  resource_group_name  = azurerm_resource_group.vm.name
  virtual_network_name = azurerm_virtual_network.vm.name
  address_prefixes     = [var.subnet_address_space]
}

# Network Security Group
resource "azurerm_network_security_group" "vm" {
  name                = "nsg-${var.vm_name}-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.vm.location
  resource_group_name = azurerm_resource_group.vm.name

  # Deny all inbound traffic
  security_rule {
    name                       = "DenyAllInbound"
    priority                   = 4000
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Allow outbound HTTPS
  security_rule {
    name                       = "AllowHTTPSOutbound"
    priority                   = 1000
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Allow outbound DNS
  security_rule {
    name                       = "AllowDNSOutbound"
    priority                   = 1010
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Udp"
    source_port_range          = "*"
    destination_port_range     = "53"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Allow outbound HTTP for apt mirrors
  security_rule {
    name                       = "AllowHTTPOutbound"
    priority                   = 1020
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Deny all other outbound traffic
  security_rule {
    name                       = "DenyAllOutbound"
    priority                   = 4000
    direction                  = "Outbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = var.tags
}

# Network Interface
resource "azurerm_network_interface" "vm" {
  name                = "nic-${var.vm_name}-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.vm.location
  resource_group_name = azurerm_resource_group.vm.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.vm.id
    private_ip_address_allocation = "Dynamic"
  }

  tags = var.tags
}

# Associate Network Security Group to Network Interface
resource "azurerm_network_interface_security_group_association" "vm" {
  network_interface_id      = azurerm_network_interface.vm.id
  network_security_group_id = azurerm_network_security_group.vm.id
}

# Virtual Machine
resource "azurerm_linux_virtual_machine" "vm" {
  name                = "${var.vm_name}-${var.environment}-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.vm.name
  location            = azurerm_resource_group.vm.location
  size                = var.vm_size
  admin_username      = var.admin_username

  # Disable password authentication and enable SSH key authentication
  disable_password_authentication = true

  network_interface_ids = [
    azurerm_network_interface.vm.id,
  ]

  # Assign the managed identity to the VM
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.vm.id]
  }

  admin_ssh_key {
    username   = var.admin_username
    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC7VIGq6B1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyz placeholder@key"
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  custom_data = base64encode(local.cloud_init_config)

  tags = var.tags
}

# Data disk
resource "azurerm_managed_disk" "vm_data" {
  name                 = "disk-${var.vm_name}-${var.environment}-data-${random_string.suffix.result}"
  location             = azurerm_resource_group.vm.location
  resource_group_name  = azurerm_resource_group.vm.name
  storage_account_type = "Standard_LRS"
  create_option        = "Empty"
  disk_size_gb         = var.data_disk_size
  tags                 = var.tags
}

# Attach data disk to VM
resource "azurerm_virtual_machine_data_disk_attachment" "vm_data" {
  managed_disk_id    = azurerm_managed_disk.vm_data.id
  virtual_machine_id = azurerm_linux_virtual_machine.vm.id
  lun                = "0"
  caching            = "ReadWrite"
}
