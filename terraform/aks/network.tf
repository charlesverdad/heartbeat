# Virtual Network for AKS
resource "azurerm_virtual_network" "aks" {
  name                = "vnet-${var.project_name}-aks-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  address_space       = ["10.1.0.0/16"]
  tags                = var.tags
}

# Subnet for AKS nodes
resource "azurerm_subnet" "aks_nodes" {
  name                 = "snet-aks-nodes"
  resource_group_name  = azurerm_resource_group.aks.name
  virtual_network_name = azurerm_virtual_network.aks.name
  address_prefixes     = ["10.1.1.0/24"]
}

# Subnet for database services (for future managed database integration)
resource "azurerm_subnet" "database" {
  name                 = "snet-database"
  resource_group_name  = azurerm_resource_group.aks.name
  virtual_network_name = azurerm_virtual_network.aks.name
  address_prefixes     = ["10.1.2.0/24"]
  
  # Enable service endpoints for database services
  service_endpoints = [
    "Microsoft.Sql",
    "Microsoft.Storage"
  ]

  # Delegate subnet to managed database services (required for some managed databases)
  delegation {
    name = "database-delegation"
    service_delegation {
      name = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action"
      ]
    }
  }
}

# Network Security Group for AKS subnet
resource "azurerm_network_security_group" "aks_nodes" {
  name                = "nsg-${var.project_name}-aks-nodes-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  tags                = var.tags

  # Allow internal VNet communication (for database connectivity)
  security_rule {
    name                       = "AllowVNetInBound"
    priority                   = 1000
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "VirtualNetwork"
  }

  # Allow outbound internet access (for pulling images, etc.)
  security_rule {
    name                       = "AllowInternetOutBound"
    priority                   = 1000
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "Internet"
  }

  # Deny all other inbound traffic
  security_rule {
    name                       = "DenyAllInBound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# Associate NSG with subnet
resource "azurerm_subnet_network_security_group_association" "aks_nodes" {
  subnet_id                 = azurerm_subnet.aks_nodes.id
  network_security_group_id = azurerm_network_security_group.aks_nodes.id
}
