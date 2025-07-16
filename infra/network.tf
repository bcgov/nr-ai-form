

resource "azapi_resource" "apim_subnet" {
  type      = "Microsoft.Network/virtualNetworks/subnets@2023-04-01"
  name      = "${local.abbrs.networkVirtualNetworksSubnets}apim-${random_id.random_deployment_suffix.hex}"
  parent_id = data.azurerm_virtual_network.vnet.id

  body = {
    properties = {

      # List of address prefixes in subnet
      addressPrefixes = ["${var.apim_subnet_prefix}"]

      # Attach to NSG
      networkSecurityGroup = {
        id = azurerm_network_security_group.apim_nsg.id
      }

      serviceEndpoints = [
        {
          service = "Microsoft.Sql"
          locations = [
            data.azurerm_resource_group.rg.location
          ]
        },
        {
          service = "Microsoft.Storage"
          locations = [
            data.azurerm_resource_group.rg.location
          ]
        },
        {
          service = "Microsoft.EventHub"
          locations = [
            data.azurerm_resource_group.rg.location
          ]
        },
        {
          service = "Microsoft.KeyVault"
          locations = [
            data.azurerm_resource_group.rg.location
          ]
        }
      ]

       routeTable = {
        id = azurerm_route_table.apim_route_table.id
      }
    }
  }
  lifecycle {
    ignore_changes = [body.properties.serviceEndpoints]
  }
  depends_on = [ azurerm_network_security_group.apim_nsg, azurerm_route_table.apim_route_table ]
  locks = [
    data.azurerm_virtual_network.vnet.id
  ]
}

resource "azapi_resource" "app_service_subnet" {
  type      = "Microsoft.Network/virtualNetworks/subnets@2023-04-01"
  name      = "${local.abbrs.networkVirtualNetworksSubnets}appservice-${random_id.random_deployment_suffix.hex}"
  parent_id = data.azurerm_virtual_network.vnet.id

  body = {
    properties = {

      # List of address prefixes in subnet
      addressPrefixes = ["${var.app_service_subnet_prefix}"]

      # Service delegations
      delegations = [
        {
          name = "app_service_delegation"
          properties = {
            serviceName = "Microsoft.Web/serverFarms"
          }
        }
      ]

      # Attach to NSG
      networkSecurityGroup = {
        id = azurerm_network_security_group.app_service_nsg.id
      }
    }
  }
  depends_on = [ azurerm_network_security_group.app_service_nsg ]
  locks = [
    data.azurerm_virtual_network.vnet.id
  ]
}

resource "azapi_resource" "privateEndpoint_subnet" {
  type      = "Microsoft.Network/virtualNetworks/subnets@2023-04-01"
  name      = "${local.abbrs.networkVirtualNetworksSubnets}privateendpoints-${random_id.random_deployment_suffix.hex}"
  parent_id = data.azurerm_virtual_network.vnet.id

  body = {
    properties = {

      # List of address prefixes in subnet
      addressPrefixes = ["${var.privateendpoint_subnet_prefix}"]

      # Attach to NSG
      networkSecurityGroup = {
        id = azurerm_network_security_group.privateendpoints_nsg.id
      }
    }
  }
  depends_on = [ azurerm_network_security_group.privateendpoints_nsg ]
  locks = [
    data.azurerm_virtual_network.vnet.id
  ]
}

resource "azurerm_network_security_group" "apim_nsg" {
  name                = "${local.abbrs.networkNetworkSecurityGroups}apim-${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name

  # Dynamic security rules from locals
  dynamic "security_rule" {
    for_each = local.apim_nsg_security_rules
    content {
      name                         = security_rule.value.name
      priority                     = security_rule.value.priority
      direction                    = security_rule.value.direction
      access                       = security_rule.value.access
      protocol                     = security_rule.value.protocol
      source_port_range            = try(security_rule.value.source_port_range, null)
      source_port_ranges           = try(security_rule.value.source_port_ranges, null)
      destination_port_range       = try(security_rule.value.destination_port_range, null)
      destination_port_ranges      = try(security_rule.value.destination_port_ranges, null)
      source_address_prefix        = try(security_rule.value.source_address_prefix, null)
      source_address_prefixes      = try(security_rule.value.source_address_prefixes, null)
      destination_address_prefix   = try(security_rule.value.destination_address_prefix, null)
      destination_address_prefixes = try(security_rule.value.destination_address_prefixes, null)
      description                  = try(security_rule.value.description, null)
    }
  }
    lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_network_security_group" "app_service_nsg" {
  # This NSG is used for the App Service subnet
  name                = "${local.abbrs.networkNetworkSecurityGroups}appservice-${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  
  # Dynamic security rules from locals
  dynamic "security_rule" {
    for_each = local.app_service_nsg_security_rules
    content {
      name                         = security_rule.value.name
      priority                     = security_rule.value.priority
      direction                    = security_rule.value.direction
      access                       = security_rule.value.access
      protocol                     = security_rule.value.protocol
      source_port_range            = try(security_rule.value.source_port_range, null)
      source_port_ranges           = try(security_rule.value.source_port_ranges, null)
      destination_port_range       = try(security_rule.value.destination_port_range, null)
      destination_port_ranges      = try(security_rule.value.destination_port_ranges, null)
      source_address_prefix        = try(security_rule.value.source_address_prefix, null)
      source_address_prefixes      = try(security_rule.value.source_address_prefixes, null)
      destination_address_prefix   = try(security_rule.value.destination_address_prefix, null)
      destination_address_prefixes = try(security_rule.value.destination_address_prefixes, null)
      description                  = try(security_rule.value.description, null)
    }
  }
  
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_network_security_group" "privateendpoints_nsg" {
  name                = "${local.abbrs.networkNetworkSecurityGroups}privateendpoints-${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  
  # Dynamic security rules from locals
  dynamic "security_rule" {
    for_each = local.privateendpoints_nsg_security_rules
    content {
      name                         = security_rule.value.name
      priority                     = security_rule.value.priority
      direction                    = security_rule.value.direction
      access                       = security_rule.value.access
      protocol                     = security_rule.value.protocol
      source_port_range            = try(security_rule.value.source_port_range, null)
      source_port_ranges           = try(security_rule.value.source_port_ranges, null)
      destination_port_range       = try(security_rule.value.destination_port_range, null)
      destination_port_ranges      = try(security_rule.value.destination_port_ranges, null)
      source_address_prefix        = try(security_rule.value.source_address_prefix, null)
      source_address_prefixes      = try(security_rule.value.source_address_prefixes, null)
      destination_address_prefix   = try(security_rule.value.destination_address_prefix, null)
      destination_address_prefixes = try(security_rule.value.destination_address_prefixes, null)
      description                  = try(security_rule.value.description, null)
    }
  }
  
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_route_table" "apim_route_table" {
  name                = "${local.abbrs.networkRouteTables}apim-${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name

  dynamic "route" {
    for_each = local.apim_route_table_routes
    content {
      name           = route.value.name
      address_prefix = route.value.address_prefix
      next_hop_type  = route.value.next_hop_type
    }
  }
      lifecycle {
    ignore_changes = [tags]
  }
}