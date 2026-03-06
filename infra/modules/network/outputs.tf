
output "container_apps_subnet_id" {
  description = "The subnet ID for Container Apps Environment."
  value       = var.deploy_network && var.app_env != "dev" && var.deployment_type == "container_apps" ? azapi_resource.container_apps_subnet[0].id : null
}

output "private_endpoint_subnet_id" {
  description = "The subnet ID for private endpoints."
  value       = var.deploy_network && var.app_env != "dev" ? azapi_resource.privateendpoints_subnet[0].id : null
  #value       = azapi_resource.privateendpoints_subnet.id
}

output "dns_servers" {
  description = "The DNS servers for the virtual network."
  value       = data.azurerm_virtual_network.main.dns_servers
}