output "storage_account_id" {
  description = "The ID of the storage account."
  value       = azurerm_storage_account.main.id
}

output "storage_account_name" {
  description = "The name of the storage account."
  value       = azurerm_storage_account.main.name
}

output "storage_account_primary_key" {
  description = "The primary access key of the storage account."
  value       = azurerm_storage_account.main.primary_access_key
  sensitive   = true
}

output "storage_blob_connection_string" {
  description = "The primary blob connection string of the storage account."
  value       = azurerm_storage_account.main.primary_blob_connection_string
  sensitive   = true
}

output "storage_container_name" {
  description = "The name of the blob container."
  value       = azurerm_storage_container.main.name
}
