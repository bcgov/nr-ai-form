resource "azurerm_cosmosdb_account" "cosmosdb_sql" {
  name                          = "${var.app_name}-cosmosdb-sql"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  offer_type                    = "Standard"
  kind                          = "GlobalDocumentDB"
  public_network_access_enabled = false

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = "canadacentral"
    failover_priority = 0
  }
  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_monitor_diagnostic_setting" "cosmosdb_sql_diagnostics" {
  name                       = "${var.app_name}-cosmosdb-diagnostics"
  target_resource_id         = azurerm_cosmosdb_account.cosmosdb_sql.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "DataPlaneRequests"
  }
  enabled_log {
    category = "MongoRequests"
  }
  enabled_log {
    category = "QueryRuntimeStatistics"
  }
  enabled_log {
    category = "PartitionKeyRUConsumption"
  }
  enabled_log {
    category = "ControlPlaneRequests"
  }

}

resource "azurerm_private_endpoint" "cosmosdb_sql_db_private_endpoint" {
  name                = "${var.app_name}-cosmosdb-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id
  private_service_connection {
    name                           = "${azurerm_cosmosdb_account.cosmosdb_sql.name}_privateserviceconnection"
    private_connection_resource_id = azurerm_cosmosdb_account.cosmosdb_sql.id
    is_manual_connection           = false
    subresource_names              = ["sql"]
  }
  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags, private_dns_zone_group]
  }
}

resource "azurerm_cosmosdb_sql_database" "cosmosdb_sql_db" {
  name                = var.cosmosdb_sql_database_name
  account_name        = azurerm_cosmosdb_account.cosmosdb_sql.name
  resource_group_name = var.resource_group_name
  throughput          = 400
}

resource "azurerm_cosmosdb_sql_container" "cosmosdb_sql_db_container" {
  name                = var.cosmosdb_sql_database_container_name
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.cosmosdb_sql.name
  database_name       = azurerm_cosmosdb_sql_database.cosmosdb_sql_db.name
  partition_key_paths = ["/partitionKey"]
}

