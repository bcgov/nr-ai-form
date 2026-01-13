# Managed Identity for App Service
#
# NOTE: Azure App Service managed identity requires Azure provider >= 4.5.0 
# for azurerm_linux_web_app_identity resource.
# Current provider version (~> 4.3) does not support this resource type.
#
# CURRENT IMPLEMENTATION: System-Assigned Identity (configured via main.tf)
# The App Service is created with system-assigned managed identity enabled,
# which is sufficient for Docker Compose and multi-container deployments.
#
# FOR FUTURE MIGRATION TO USER-ASSIGNED IDENTITY:
# When upgrading Azure provider to >= 4.5.0, uncomment the resources below
# to enable more granular identity and RBAC management.
#
# ============================================================================
# TERRAFORM RESOURCES FOR FUTURE USE (Uncomment when provider >= 4.5.0)
# ============================================================================
#
# # Create a user-assigned identity for the App Service
# resource "azurerm_user_assigned_identity" "api" {
#   name                = "${var.app_name}-api-identity"
#   resource_group_name = var.resource_group_name
#   location            = var.location
#   tags                = var.common_tags
#
#   lifecycle {
#     ignore_changes = [tags]
#   }
# }
#
# # Assign the user-assigned identity to the App Service
# resource "azurerm_linux_web_app_identity" "api" {
#   web_app_id   = azurerm_linux_web_app.api.id
#   type         = "UserAssigned"
#   identity_ids = [azurerm_user_assigned_identity.api.id]
# }
#
# # Get current ACR for pull permissions
# data "azurerm_container_registry" "acr" {
#   count               = var.container_registry_url != "" ? 1 : 0
#   name                = split("/", var.container_registry_url)[0]
#   resource_group_name = var.resource_group_name
# }
#
# # Assign AcrPull role to the user-assigned identity for ACR access
# resource "azurerm_role_assignment" "api_acr_pull" {
#   count              = var.container_registry_url != "" ? 1 : 0
#   scope              = data.azurerm_container_registry.acr[0].id
#   role_definition_name = "AcrPull"
#   principal_id       = azurerm_user_assigned_identity.api.principal_id
# }
