# Azure App Service Module for Chisel Proxy
# Deploys Chisel proxy to App Service with Docker container support

# App Service Plan (required for App Service)
resource "azurerm_service_plan" "chisel" {
  name                = var.app_service_plan_name
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = "Linux"
  sku_name            = var.sku_name

  tags = var.common_tags
}

# App Service for Chisel
resource "azurerm_linux_web_app" "chisel" {
  name                = var.app_service_name
  location            = var.location
  resource_group_name = var.resource_group_name
  service_plan_id     = azurerm_service_plan.chisel.id

  # Docker configuration
  app_settings = {
    DOCKER_REGISTRY_SERVER_URL          = "https://${var.registry_server}"
    DOCKER_REGISTRY_SERVER_USERNAME     = var.registry_username
    DOCKER_REGISTRY_SERVER_PASSWORD     = var.registry_password
    WEBSITES_ENABLE_APP_SERVICE_STORAGE = "false"
    WEBSITES_PORT                       = var.chisel_port

    # Chisel configuration
    CHISEL_AUTH          = "tunnel:${var.chisel_password}"
    CHISEL_PORT          = var.chisel_port
    CHISEL_HOST          = var.chisel_host
    CHISEL_ENABLE_SOCKS5 = var.enable_socks5 ? "true" : "false"
    PORT                 = var.chisel_port
    MAX_RETRIES          = var.max_retries
    DELAY_SECONDS        = var.delay_seconds
  }

  site_config {
    always_on                = true
    minimum_tls_version      = "1.2"
    http2_enabled            = true
    remote_debugging_enabled = false
    remote_debugging_version = "VS2019"

    # Docker configuration
    docker_image_name          = "${var.registry_server}/${var.docker_image_name}"
    docker_registry_server_url = "https://${var.registry_server}"

    # Health check configuration
    health_check_path = var.health_check_path

    # Startup command (optional - set if needed)
    # app_command_line = ""

    # Container startup
    app_service_logs {
      disk_quota_mb         = 35
      retention_period_days = 0
    }
  }

  # Enable managed identity for potential future use (e.g., Key Vault integration)
  identity {
    type = "SystemAssigned"
  }

  https_only = true

  tags = var.common_tags

  depends_on = [
    azurerm_service_plan.chisel
  ]
}

# Diagnostic Settings for App Service
resource "azurerm_monitor_diagnostic_setting" "chisel_appservice" {
  name                       = "${var.app_service_name}-diagnostics"
  target_resource_id         = azurerm_linux_web_app.chisel.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "AppServiceHTTPLogs"
    enabled  = true

    retention_policy {
      enabled = false
    }
  }

  enabled_log {
    category = "AppServiceConsoleLogs"
    enabled  = true

    retention_policy {
      enabled = false
    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true

    retention_policy {
      enabled = false
    }
  }
}

# Optional: Auto-scale configuration for high availability
resource "azurerm_monitor_autoscale_setting" "chisel" {
  count               = var.enable_autoscale ? 1 : 0
  name                = "${var.app_service_name}-autoscale"
  location            = var.location
  resource_group_name = var.resource_group_name
  target_resource_id  = azurerm_service_plan.chisel.id

  profile {
    name = "default"

    capacity {
      default = var.min_instances
      minimum = var.min_instances
      maximum = var.max_instances
    }

    rule {
      metric_trigger {
        metric_name        = "CpuPercentage"
        metric_resource_id = azurerm_service_plan.chisel.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT5M"
        operator           = "GreaterThan"
        threshold          = 70
      }

      scale_action {
        direction = "Increase"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT5M"
      }
    }

    rule {
      metric_trigger {
        metric_name        = "CpuPercentage"
        metric_resource_id = azurerm_service_plan.chisel.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT5M"
        operator           = "LessThan"
        threshold          = 30
      }

      scale_action {
        direction = "Decrease"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT5M"
      }
    }
  }
}
