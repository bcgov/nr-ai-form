output "resource_group_name" {
  value = data.azurerm_resource_group.rg.name
}

/* output "container_app_fqdn" {
  value = azurerm_container_app.container_app.latest_revision_fqdn
  description = "The FQDN of the Container App"
}

output "container_app_url" {
  value = "https://${azurerm_container_app.container_app.latest_revision_fqdn}"
  description = "The full URL of the Container App"
} */