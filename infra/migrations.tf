# -------------
# One-time state migrations — safe to keep indefinitely, no-op once removed
# Terraform 1.7+ `removed` blocks handle these declaratively so CI shell doesn't have to.
# -------------

# Migration: azurerm_subnet → azapi_resource for the Container Apps subnet
# The subnet is now managed by azapi_resource.container_apps_subnet in the network module.
removed {
  from = module.network.azurerm_subnet.container_apps_subnet[0]
  lifecycle { destroy = false }
}

# Migration: NSG association for the Container Apps subnet was dropped when moving to azapi
# (azapi inline body handles the NSG association, no separate resource needed)
removed {
  from = module.network.azurerm_subnet_network_security_group_association.container_apps[0]
  lifecycle { destroy = false }
}
