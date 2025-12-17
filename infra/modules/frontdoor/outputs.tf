output "firewall_policy_id" {
  description = "The ID of the Front Door firewall policy."
  value       = azurerm_cdn_frontdoor_firewall_policy.frontend_firewall_policy.id

}

output "frontdoor_id" {
  description = "The name of the Front Door endpoint."
  value       = azurerm_cdn_frontdoor_profile.frontend_frontdoor.id
}

output "frontdoor_resource_guid" {
  description = "The resource GUID of the Front Door profile."
  value       = azurerm_cdn_frontdoor_profile.frontend_frontdoor.resource_guid
}

output "frontdoor_endpoint_hostname" {
  description = "The hostname of the Front Door endpoint."
  value       = try(azurerm_cdn_frontdoor_endpoint.frontend_endpoint[0].host_name, "")
}
