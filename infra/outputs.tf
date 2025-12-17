output "cdn_frontdoor_endpoint_url" {
  description = "The URL of the CDN Front Door endpoint"
  value       = "https://${module.frontdoor.frontdoor_endpoint_hostname}"
}

output "container_apps_environment_id" {
  description = "The ID of the Container Apps Environment"
  value       = module.container_apps.container_apps_environment_id
}

output "container_apps_environment_name" {
  description = "The name of the Container Apps Environment"
  value       = module.container_apps.container_apps_environment_name
}

output "backend_container_app_id" {
  description = "The ID of the backend Container App"
  value       = module.container_apps.backend_container_app_id
}

output "backend_container_app_name" {
  description = "The name of the backend Container App"
  value       = module.container_apps.backend_container_app_name
}

output "backend_container_app_fqdn" {
  description = "The internal FQDN of the backend Container App"
  value       = module.container_apps.backend_container_app_fqdn
  sensitive   = true
}

output "backend_container_app_url" {
  description = "The internal URL of the backend Container App"
  value       = module.container_apps.backend_container_app_url
  sensitive   = true
}
