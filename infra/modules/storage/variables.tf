variable "app_name" {
  description = "Name of the application"
  type        = string
  nullable    = false
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  nullable    = false
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  nullable    = false
}

variable "resource_group_name" {
  description = "The name of the resource group."
  type        = string
  nullable    = false
}

variable "private_endpoint_subnet_id" {
  description = "The ID of the subnet for the private endpoint."
  type        = string
  nullable    = false
}

variable "log_analytics_workspace_id" {
  description = "The resource ID of the Log Analytics workspace for diagnostics."
  type        = string
  nullable    = false
}

variable "container_name" {
  description = "Blob container holding form definitions and prompt templates (AZURE_BLOBSTORAGE_CONTAINER)."
  type        = string
  nullable    = false
}

variable "account_replication_type" {
  description = "Storage replication type (LRS, ZRS, GRS, GZRS, ...)."
  type        = string
  default     = "ZRS"
}

variable "blob_soft_delete_retention_days" {
  description = "Days to retain deleted blobs and containers."
  type        = number
  default     = 7
}

variable "public_network_access_enabled" {
  description = "Allow public access to the storage account. Keep false in prod; the Container App reaches it through the private endpoint."
  type        = bool
  default     = false
}
