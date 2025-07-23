resource "azurerm_api_management" "apim" {
  name                 = "${local.abbrs.apiManagementService}${random_id.random_deployment_suffix.hex}"
  location             = data.azurerm_resource_group.rg.location
  resource_group_name  = data.azurerm_resource_group.rg.name
  virtual_network_type = var.apim_virtual_network_type
  virtual_network_configuration {
    subnet_id = azapi_resource.apim_subnet.id
  }
  publisher_email = var.publisher_email
  publisher_name  = var.publisher_name
  sku_name        = "${var.sku}_${var.sku_count}"
  identity {
    type = "SystemAssigned"
  }
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_monitor_diagnostic_setting" "apim_diagnostics" {
  name                       = "${local.abbrs.apiManagementService}${random_id.random_deployment_suffix.hex}_diagnostics"
  target_resource_id         = azurerm_api_management.apim.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.log_analytics_workspace.id

  enabled_log {
    category = "GatewayLogs"
  }
  enabled_log {
    category = "WebSocketConnectionLogs"
  }
  enabled_log {
    category = "DeveloperPortalAuditLogs"
  }
  enabled_log {
    category = "GatewayLlmLogs"
  }
  enabled_metric {
    category = "AllMetrics"
  }
}

resource "azurerm_api_management_logger" "apim_logger" {
  name                = "${local.abbrs.apiManagementService}${random_id.random_deployment_suffix.hex}_logger"
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = data.azurerm_resource_group.rg.name
  resource_id         = azurerm_application_insights.app_insights.id

  application_insights {
    instrumentation_key = azurerm_application_insights.app_insights.instrumentation_key
  }
}

resource "azurerm_api_management_api" "nr-ai-form" {
  name                = "nr-ai-form"
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = data.azurerm_resource_group.rg.name
  revision            = "1"
  display_name        = "NR AI Form API"
  path                = "nr-ai-form"
  protocols           = ["https"]
  service_url         = "https://${azurerm_linux_web_app.app_service.default_hostname}"
  import {
    content_format = "openapi"
    content_value  = file("./../src/docs/openapi.yaml")
  }
}

resource "azurerm_api_management_api_diagnostic" "nr-ai-form" {
  identifier             = "applicationinsights"
  api_management_name    = azurerm_api_management.apim.name
  resource_group_name    = data.azurerm_resource_group.rg.name
  api_name               = azurerm_api_management_api.nr-ai-form.name
  api_management_logger_id = azurerm_api_management_logger.apim_logger.id

  sampling_percentage    = 100

  frontend_request {
    body_bytes = 512
    headers_to_log = ["*"]
  }

  frontend_response {
    body_bytes = 512
    headers_to_log = ["*"]
  }

  backend_request {
    body_bytes = 512
    headers_to_log = ["*"]
  }

  backend_response {
    body_bytes = 512
    headers_to_log = ["*"]
  }
}

