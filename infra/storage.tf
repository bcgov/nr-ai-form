resource "azurerm_storage_account" "storage_account" {
    name                = "${local.abbrs.storageStorageAccounts}${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name

  account_kind             = "StorageV2"
  account_tier             = "Standard"
  account_replication_type = "LRS"

  ## Network access configuration
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
}

resource "azurerm_monitor_diagnostic_setting" "storage_account_diagnostics" {
  name                       = "${local.abbrs.storageStorageAccounts}${random_id.random_deployment_suffix.hex}_diagnostics"
  target_resource_id         = azurerm_storage_account.storage_account.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.log_analytics_workspace.id

  enabled_log {
    category = "StorageRead"
  }
  enabled_log {
    category = "StorageWrite"
  }
    enabled_metric {
    category = "AllMetrics"
  }
}

resource "azurerm_private_endpoint" "app_service_private_endpoint" {
  name                = "${local.abbrs.privateEndpoint}${local.abbrs.storageStorageAccounts}${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  subnet_id           = azapi_resource.privateEndpoint_subnet.id
  private_service_connection {
    name                           = "${azurerm_storage_account.storage_account.name}_privateserviceconnection"
    private_connection_resource_id = azurerm_storage_account.storage_account.id
    is_manual_connection           = false
    subresource_names              = ["blob", "queue", "table", "file"]
  }
  lifecycle {
    ignore_changes = [tags, private_dns_zone_group]
  }
}