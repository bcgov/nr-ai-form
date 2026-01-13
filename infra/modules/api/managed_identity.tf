# Managed Identity for App Service
# Used for ACR authentication and sidecar container access

resource "azurerm_user_assigned_identity" "api" {
  name                = "${var.app_name}-api-identity"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.common_tags

  lifecycle {
    ignore_changes = [tags]
  }
}

# Assign the user-assigned identity to the App Service
resource "azurerm_linux_web_app_identity" "api" {
  web_app_id      = azurerm_linux_web_app.api.id
  type            = "UserAssigned"
  identity_ids    = [azurerm_user_assigned_identity.api.id]
}

# Get current ACR for pull permissions
data "azurerm_container_registry" "acr" {
  count               = var.container_registry_url != "" ? 1 : 0
  name                = split("/", var.container_registry_url)[0]
  resource_group_name = var.resource_group_name
}

# Assign AcrPull role to the user-assigned identity for ACR access
resource "azurerm_role_assignment" "api_acr_pull" {
  scope              = data.azurerm_container_registry.acr[0].id
  role_definition_name = "AcrPull"
  principal_id       = azurerm_user_assigned_identity.api.principal_id
}
