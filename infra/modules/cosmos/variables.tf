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

variable "private_endpoint_subnet_id" {
  description = "The ID of the subnet for the private endpoint."
  type        = string
  nullable    = false
}

variable "resource_group_name" {
  description = "The name of the resource group to create."
  type        = string
  nullable    = false
}

variable "cosmosdb_sql_database_container_name" {
  type        = string
  default     = "cosmosContainer"
  description = "Name of the Cosmos DB SQL database container."
}


variable "cosmosdb_sql_database_name" {
  type        = string
  default     = "cosmosDatabase"
  description = "Name of the Cosmos DB SQL database."
}

variable "log_analytics_workspace_id" {
  description = "The resource ID of the Log Analytics workspace for diagnostics."
  type        = string
  nullable    = false
}