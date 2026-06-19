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
  admin_enabled       = true
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

  site_config {
    always_on                               = true
    container_registry_use_managed_identity = false

    application_stack {
      docker_image_name        = "chisel_server:latest"
      docker_registry_url      = azurerm_container_registry.chisel.login_server
      docker_registry_username = azurerm_container_registry.chisel.admin_username
      docker_registry_password = azurerm_container_registry.chisel.admin_password
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
