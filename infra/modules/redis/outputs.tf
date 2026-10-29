output "redis_id" {
  description = "The ID of the Azure Managed Redis instance."
  value       = azurerm_managed_redis.main.id
}

output "redis_name" {
  description = "The name of the Azure Managed Redis instance."
  value       = azurerm_managed_redis.main.name
}

output "redis_hostname" {
  description = "The hostname of the Azure Managed Redis instance."
  value       = azurerm_managed_redis.main.hostname
}

output "redis_port" {
  description = "The port of the default Redis database."
  value       = azurerm_managed_redis.main.default_database[0].port
}

output "redis_primary_access_key" {
  description = "The primary access key of the default Redis database."
  value       = azurerm_managed_redis.main.default_database[0].primary_access_key
  sensitive   = true
}
