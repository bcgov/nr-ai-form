output "cdn_frontdoor_endpoint_url" {
  description = "The URL of the CDN Front Door endpoint"
  value       = "https://${module.frontdoor.frontdoor_endpoint_hostname}"
}

# Container Apps outputs (only available when deployment_type = "container_apps")
output "container_apps_environment_id" {
  description = "The ID of the Container Apps Environment"
  value       = try(module.container_apps[0].container_apps_environment_id, null)
}

output "container_apps_environment_name" {
  description = "The name of the Container Apps Environment"
  value       = try(module.container_apps[0].container_apps_environment_name, null)
}

output "backend_container_app_id" {
  description = "The ID of the backend Container App"
  value       = try(module.container_apps[0].backend_container_app_id, null)
}

output "backend_container_app_name" {
  description = "The name of the backend Container App"
  value       = try(module.container_apps[0].backend_container_app_name, null)
}

output "backend_container_app_fqdn" {
  description = "The internal FQDN of the backend Container App"
  value       = try(module.container_apps[0].backend_container_app_fqdn, null)
  sensitive   = true
}

output "backend_container_app_url" {
  description = "The internal URL of the backend Container App"
  value       = try(module.container_apps[0].backend_container_app_url, null)
  sensitive   = true
}

