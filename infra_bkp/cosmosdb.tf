resource "azurerm_cosmosdb_account" "cosmosdb_sql" {
  name                          = "${local.abbrs.documentDBDatabaseAccounts}${random_id.random_deployment_suffix.hex}"
  location                      = data.azurerm_resource_group.rg.location
  resource_group_name           = data.azurerm_resource_group.rg.name
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
}

resource "azurerm_monitor_diagnostic_setting" "cosmosdb_sql_diagnostics" {
  name                       = "${local.abbrs.documentDBDatabaseAccounts}${random_id.random_deployment_suffix.hex}_diagnostics"
  target_resource_id         = azurerm_cosmosdb_account.cosmosdb_sql.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.log_analytics_workspace.id

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
  name                = "${local.abbrs.privateEndpoint}${local.abbrs.documentDBDatabaseAccounts}${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  subnet_id           = azapi_resource.privateEndpoint_subnet.id
  private_service_connection {
    name                           = "${azurerm_cosmosdb_account.cosmosdb_sql.name}_privateserviceconnection"
    private_connection_resource_id = azurerm_cosmosdb_account.cosmosdb_sql.id
    is_manual_connection           = false
    subresource_names              = ["sql"]
  }
  lifecycle {
    ignore_changes = [tags, private_dns_zone_group]
  }
}

resource "azurerm_cosmosdb_sql_database" "cosmosdb_sql_db" {
  name                = var.cosmosdb_sql_database_name
  account_name        = azurerm_cosmosdb_account.cosmosdb_sql.name
  resource_group_name = data.azurerm_resource_group.rg.name
  throughput          = 400
}

resource "azurerm_cosmosdb_sql_container" "cosmosdb_sql_db_container" {
  name                = var.cosmosdb_sql_database_container_name
  resource_group_name = data.azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmosdb_sql.name
  database_name       = azurerm_cosmosdb_sql_database.cosmosdb_sql_db.name
  partition_key_paths = ["/partitionKey"]
}

// Assign the App Service's managed identity to the Cosmos DB SQL Database with Data Contributor role

resource "azurerm_cosmosdb_sql_role_assignment" "cosmosdb_role_assignment_app_service_data_contributor" {
  resource_group_name = data.azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmosdb_sql.name
  role_definition_id  = "${azurerm_cosmosdb_account.cosmosdb_sql.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = azurerm_linux_web_app.app_service.identity[0].principal_id
  scope               = azurerm_cosmosdb_account.cosmosdb_sql.id
}
