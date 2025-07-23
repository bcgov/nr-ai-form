output "api_managed_identity_principal_id" {
  description = "The principal ID of the API's managed identity to assign roles in Cosmos DB."
  value       = azurerm_linux_web_app.api.identity[0].principal_id
}

output "frontdoor_api_endpoint" {
  description = "The API endpoint"
  value       = "https://${azurerm_cdn_frontdoor_endpoint.api_fd_endpoint.host_name}/"
}