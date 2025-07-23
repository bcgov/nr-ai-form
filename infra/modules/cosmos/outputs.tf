output "account_name" {
  description = "The name of the Cosmos DB account."
  value       = azurerm_cosmosdb_account.cosmosdb_sql.name

}

output "account_id" {
  description = "The ID of the Cosmos DB account."
  value       = azurerm_cosmosdb_account.cosmosdb_sql.id
}

output "cosmosdb_endpoint" {
  description = "The endpoint of the Cosmos DB account."
  value       = azurerm_cosmosdb_account.cosmosdb_sql.endpoint
}
output "cosmosdb_sql_database_name" {
  description = "The name of the Cosmos DB SQL database."
  value       = azurerm_cosmosdb_sql_database.cosmosdb_sql_db.name
}
output "cosmosdb_sql_database_container_name" {
  description = "The name of the Cosmos DB SQL database container."
  value       = azurerm_cosmosdb_sql_container.cosmosdb_sql_db_container.name

}