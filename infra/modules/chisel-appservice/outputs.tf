output "chisel_app_service_name" {
  value       = azurerm_linux_web_app.chisel.name
  description = "Name of the Chisel App Service"
}

output "chisel_app_service_id" {
  value       = azurerm_linux_web_app.chisel.id
  description = "Resource ID of the Chisel App Service"
}

output "chisel_fqdn" {
  value       = azurerm_linux_web_app.chisel.default_hostname
  description = "FQDN of the Chisel App Service"
}

output "chisel_url" {
  value       = "https://${azurerm_linux_web_app.chisel.default_hostname}"
  description = "Public HTTPS URL of the Chisel proxy"
}

output "health_check_url" {
  value       = "https://${azurerm_linux_web_app.chisel.default_hostname}${var.health_check_path}"
  description = "Health check endpoint URL"
}

output "app_service_plan_id" {
  value       = azurerm_service_plan.chisel.id
  description = "Resource ID of the App Service Plan"
}

output "app_service_plan_name" {
  value       = azurerm_service_plan.chisel.name
  description = "Name of the App Service Plan"
}

output "principal_id" {
  value       = azurerm_linux_web_app.chisel.identity[0].principal_id
  description = "Principal ID for the App Service managed identity"
}
