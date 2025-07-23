output "cloudbeaver_app_service_url" {
  description = "The URL of the CloudBeaver App Service"
  value       = module.backend.cloudbeaver_app_service_url != null ? "https://${module.backend.cloudbeaver_app_service_url}" : null
}

output "cdn_frontdoor_endpoint_url" {
  description = "The URL of the CDN Front Door endpoint"
  value       = module.frontend.frontend_url
}