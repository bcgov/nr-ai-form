resource "azurerm_search_service" "main" {
  name                          = "${var.app_name}-search"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  sku                           = var.search_sku
  replica_count                 = var.replica_count
  partition_count               = var.partition_count
  semantic_search_sku           = var.semantic_search_sku
  local_authentication_enabled  = true # conversationagent authenticates with AZURE_SEARCH_API_KEY
  public_network_access_enabled = var.public_network_access_enabled

  identity {
    type = "SystemAssigned"
  }

  tags = var.common_tags
  lifecycle {
    ignore_changes  = [tags]
    prevent_destroy = true
  }
}

resource "azurerm_monitor_diagnostic_setting" "search_diagnostics" {
  name                       = "${var.app_name}-search-diagnostics"
  target_resource_id         = azurerm_search_service.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "OperationLogs"
  }
}

resource "azurerm_private_endpoint" "search_private_endpoint" {
  name                = "${var.app_name}-search-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id
  private_service_connection {
    name                           = "${azurerm_search_service.main.name}_privateserviceconnection"
    private_connection_resource_id = azurerm_search_service.main.id
    is_manual_connection           = false
    subresource_names              = ["searchService"]
  }
  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags, private_dns_zone_group]
  }
}
