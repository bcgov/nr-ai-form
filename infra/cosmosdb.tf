resource "azurerm_cosmosdb_account" "cosmosdb_sql" {
  name                = "${local.abbrs.documentDBDatabaseAccounts}${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"
  public_network_access_enabled = false
  
  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = "canadacentral"
    failover_priority = 0
  }
}

resource "azurerm_cosmosdb_sql_database" "cosmosdb_sql_db" {
  name                = "${local.abbrs.documentDBDatabaseAccounts}database-${random_id.random_deployment_suffix.hex}"
  account_name        = azurerm_cosmosdb_account.cosmosdb_sql.name
  resource_group_name = data.azurerm_resource_group.rg.name
  throughput          = 400
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
}

resource "azurerm_cosmosdb_sql_role_definition" "cosmosdb_sql_role_definition" {
  name                = "app-service-cosmosdb-role"
  resource_group_name = data.azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmosdb_sql.name
  type                = "CustomRole"
  assignable_scopes   = ["${azurerm_cosmosdb_account.cosmosdb_sql.id}/dbs/${azurerm_cosmosdb_sql_database.cosmosdb_sql_db.name}"]

  permissions {
    data_actions = [
      "Microsoft.DocumentDB/databaseAccounts/readMetadata",
      "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*",
      "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/*"
    ]
  }
}

resource "azurerm_cosmosdb_sql_role_assignment" "app_service_cosmosdb_assignment" {
  resource_group_name = data.azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmosdb_sql.name
  role_definition_id  = azurerm_cosmosdb_sql_role_definition.cosmosdb_sql_role_definition.id
  principal_id        = azurerm_linux_web_app.app_service.identity[0].principal_id
  scope               = "${azurerm_cosmosdb_account.cosmosdb_sql.id}/dbs/${azurerm_cosmosdb_sql_database.cosmosdb_sql_db.name}"
}

# Add role assignment for the developer (you) for local development and testing
resource "azurerm_cosmosdb_sql_role_assignment" "developer_cosmosdb_assignment" {
  resource_group_name = data.azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmosdb_sql.name
  role_definition_id  = azurerm_cosmosdb_sql_role_definition.cosmosdb_sql_role_definition.id
  principal_id        = "9269b378-2d2a-4581-beba-efb46569c16c" # Your user object ID
  scope               = "${azurerm_cosmosdb_account.cosmosdb_sql.id}/dbs/${azurerm_cosmosdb_sql_database.cosmosdb_sql_db.name}"
}