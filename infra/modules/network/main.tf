data "azurerm_virtual_network" "main" {
  name                = var.vnet_name
  resource_group_name = var.vnet_resource_group_name
}

# NSG for privateendpoints subnet
resource "azurerm_network_security_group" "privateendpoints" {
  name                = "${var.resource_group_name}-pe-nsg"
  location            = var.location
  resource_group_name = var.vnet_resource_group_name

  security_rule {
    name                       = "AllowInboundFromApp"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_address_prefix      = local.app_service_subnet_cidr
    destination_address_prefix = local.private_endpoints_subnet_cidr
    destination_port_range     = "*"
    source_port_range          = "*"
  }

  security_rule {
    name                       = "AllowOutboundToApp"
    priority                   = 101
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    destination_address_prefix = local.app_service_subnet_cidr
    source_address_prefix      = local.private_endpoints_subnet_cidr
    source_port_range          = "*"
    destination_port_range     = "*"
  }

  tags = var.common_tags
  lifecycle {
    ignore_changes = [
      tags
    ]
  }
}

# NSG for app service subnet
resource "azurerm_network_security_group" "app_service" {
  name                = "${var.resource_group_name}-as-nsg"
  location            = var.location
  resource_group_name = var.vnet_resource_group_name

  security_rule {
    name                       = "AllowAppFromPrivateEndpoint"
    priority                   = 102
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_address_prefix      = local.private_endpoints_subnet_cidr
    source_port_range          = "*"
    destination_address_prefix = local.app_service_subnet_cidr
    destination_port_range     = "*"
  }

  security_rule {
    name                       = "AllowAppToPrivateEndpoint"
    priority                   = 103
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    destination_address_prefix = local.private_endpoints_subnet_cidr
    source_address_prefix      = local.app_service_subnet_cidr
    source_port_range          = "*"
    destination_port_range     = "*"
  }

  security_rule {
    name                       = "AllowAppFromInternet"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_address_prefix      = "*"
    source_port_range          = "*"
    destination_address_prefix = local.app_service_subnet_cidr
    destination_port_ranges    = ["80", "443"]
  }
  security_rule {
    name                       = "AllowAppOutboundToInternet"
    priority                   = 120
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_address_prefix      = local.app_service_subnet_cidr
    destination_address_prefix = "*"
    source_port_range          = "*"
    destination_port_ranges    = ["80", "443"]
  }
  tags = var.common_tags
  lifecycle {
    ignore_changes = [
      tags
    ]
  }
}

# Subnets
resource "azapi_resource" "privateendpoints_subnet" {
  type      = "Microsoft.Network/virtualNetworks/subnets@2023-04-01"
  name      = var.private_endpoint_subnet_name
  parent_id = data.azurerm_virtual_network.main.id
  locks     = [data.azurerm_virtual_network.main.id]
  body = {
    properties = {
      addressPrefix = local.private_endpoints_subnet_cidr
      networkSecurityGroup = {
        id = azurerm_network_security_group.privateendpoints.id
      }
    }
  }
  response_export_values = ["*"]
}

resource "azapi_resource" "app_service_subnet" {
  type      = "Microsoft.Network/virtualNetworks/subnets@2023-04-01"
  name      = var.apps_service_subnet_name
  parent_id = data.azurerm_virtual_network.main.id
  locks     = [data.azurerm_virtual_network.main.id]
  body = {
    properties = {
      addressPrefix = local.app_service_subnet_cidr
      networkSecurityGroup = {
        id = azurerm_network_security_group.app_service.id
      }
      delegations = [
        {
          name = "app-service-delegation"
          properties = {
            serviceName = "Microsoft.Web/serverFarms"
          }
        }
      ]
    }
  }
  response_export_values = ["*"]
}

