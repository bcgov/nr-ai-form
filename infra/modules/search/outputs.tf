output "search_service_id" {
  description = "The ID of the Azure AI Search service."
  value       = azurerm_search_service.main.id
}

output "search_service_name" {
  description = "The name of the Azure AI Search service."
  value       = azurerm_search_service.main.name
}

output "search_endpoint" {
  description = "The endpoint URL of the Azure AI Search service."
  value       = "https://${azurerm_search_service.main.name}.search.windows.net"
}

output "search_primary_key" {
  description = "The primary admin key of the Azure AI Search service."
  value       = azurerm_search_service.main.primary_key
  sensitive   = true
}

output "search_principal_id" {
  description = "The principal ID of the search service system-assigned identity."
  value       = azurerm_search_service.main.identity[0].principal_id
}
