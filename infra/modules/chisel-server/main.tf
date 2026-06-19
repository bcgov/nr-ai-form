# =========================================================
# Azure App Service - Chisel Server
# =========================================================
# This is the centralized tunnel server that clients connect to

locals {
  chisel_server_name = "${var.app_name}-chisel-server-${var.environment}"
}

# Container Registry for Chisel Server image
resource "azurerm_container_registry" "chisel" {
  name                = replace("${var.app_name}chiselreg${var.environment}", "-", "")
  location            = var.location
  resource_group_name = var.resource_group_name
  admin_enabled       = false
  sku                 = "Basic"

  tags = var.common_tags
}

# App Service Plan
resource "azurerm_service_plan" "chisel_server" {
  name                = "${local.chisel_server_name}-plan"
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = "Linux"
  sku_name            = "B1" # Basic tier - sufficient for tunnel

  tags = var.common_tags
}

# App Service
resource "azurerm_linux_web_app" "chisel_server" {
  name                = local.chisel_server_name
  location            = var.location
  resource_group_name = var.resource_group_name
  service_plan_id     = azurerm_service_plan.chisel_server.id

  https_only = true

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on                               = true
    websockets_enabled                      = true
    container_registry_use_managed_identity = true

    application_stack {
      docker_image_name        = "chisel-server:latest"
      docker_registry_url      = "https://${azurerm_container_registry.chisel.login_server}"
    }
  }

  app_settings = {
    # Chisel Server Configuration
    "CHISEL_AUTH"          = var.chisel_server_auth # "user:password"
    "CHISEL_ENABLE_SOCKS5" = "true"
    "CHISEL_PORT"          = "80" # App Service converts to 443
    "WEBSITES_PORT"        = "80"
  }

  tags = merge(
    var.common_tags,
    {
      "component" = "chisel-server"
    }
  )

  lifecycle {
    ignore_changes = [app_settings["WEBSITE_HOSTNAME"]]
  }
}

resource "azurerm_role_assignment" "chisel_server_acr_pull" {
  scope                = azurerm_container_registry.chisel.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_linux_web_app.chisel_server.identity[0].principal_id
}

# Get the Chisel Server URL
output "chisel_server_url" {
  value       = "https://${azurerm_linux_web_app.chisel_server.default_hostname}"
  description = "Chisel Server endpoint URL for clients"
}

output "chisel_server_auth_required" {
  value       = var.chisel_server_auth
  description = "Chisel server authentication credentials"
  sensitive   = true
}
