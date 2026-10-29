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

variable "sku_name" {
  description = "Azure Managed Redis SKU (Balanced_B0, Balanced_B1, MemoryOptimized_M10, ...)."
  type        = string
  default     = "Balanced_B1"
}

variable "high_availability_enabled" {
  description = "Replicate data across a second node. Keep true in prod for the SLA."
  type        = bool
  default     = true
}

variable "eviction_policy" {
  description = "Eviction policy when memory is full. Session keys carry a TTL, so volatile-lru evicts only expiring keys."
  type        = string
  default     = "VolatileLRU"
}

variable "public_network_access_enabled" {
  description = "Allow public access to Redis. Keep false in prod; the Container App reaches it through the private endpoint."
  type        = bool
  default     = false
}
