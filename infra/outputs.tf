output "cdn_frontdoor_endpoint_url" {
  description = "The URL of the CDN Front Door endpoint"
  value       = module.api.frontdoor_api_endpoint
}