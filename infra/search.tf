resource "azurerm_search_service" "search_service" {
  name                = "${local.abbrs.searchSearchServices}${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  sku                 = "standard"

  public_network_access_enabled = false

  local_authentication_enabled = false
}

resource "azurerm_monitor_diagnostic_setting" "search_service_diagnostics" {
  name                       = "${local.abbrs.searchSearchServices}${random_id.random_deployment_suffix.hex}_diagnostics"
  target_resource_id         = azurerm_search_service.search_service.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.log_analytics_workspace.id

  enabled_log {
    category = "OperationLogs"
  }
    enabled_metric {
    category = "AllMetrics"
  }
}

resource "azurerm_private_endpoint" "search_service_private_endpoint" {
  name                = "${local.abbrs.privateEndpoint}${local.abbrs.searchSearchServices}${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  subnet_id           = azapi_resource.privateEndpoint_subnet.id
  private_service_connection {
    name                           = "${azurerm_search_service.search_service.name}_privateserviceconnection"
    private_connection_resource_id = azurerm_search_service.search_service.id
    is_manual_connection           = false
    subresource_names              = ["searchService"]
  }
  lifecycle {
    ignore_changes = [tags, private_dns_zone_group]
  }
}