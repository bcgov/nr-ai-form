resource "azurerm_api_management" "apim" {
  name                = "${local.abbrs.apiManagementService}${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  virtual_network_type = var.apim_virtual_network_type
  virtual_network_configuration {
    subnet_id = azapi_resource.apim_subnet.id
  }
  publisher_email     = var.publisher_email
  publisher_name      = var.publisher_name
  sku_name            = "${var.sku}_${var.sku_count}"
  identity {
    type = "SystemAssigned"
  }
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_api_management_logger" "apim_logger" {
  name                = "apimlogger"
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = data.azurerm_resource_group.rg.name

  application_insights {
    instrumentation_key = azurerm_application_insights.app_insights.instrumentation_key
  }
}

resource "azurerm_api_management_api" "nr-permitting-api" {
  name                = "nr-permitting-api"
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = data.azurerm_resource_group.rg.name
  revision            = "1"
  display_name        = "NR Permitting API"
  path                = "nr-permitting"
  protocols           = ["https"]
  service_url         = "https://${azurerm_linux_web_app.app_service.default_hostname}"
   import {
    content_format = "openapi"
    content_value  = file("./../src/docs/openapi-azure.yaml")
  } 
}