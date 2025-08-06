
output "app_service_subnet_id" {
  description = "The subnet ID for the App Service."
  value       = azapi_resource.app_service_subnet.id
}

output "private_endpoint_subnet_id" {
  description = "The subnet ID for private endpoints."
  value       = azapi_resource.privateendpoints_subnet.id
}

output "dns_servers" {
  description = "The DNS servers for the virtual network."
  value       = data.azurerm_virtual_network.main.dns_servers
}