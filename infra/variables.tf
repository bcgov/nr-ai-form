# -------------
# Root Variables for Azure Infrastructure
# -------------

variable "api_image" {
  description = "The image for the API container"
  type        = string
}

variable "app_env" {
  description = "Application environment (dev, test, prod)"
  type        = string
}

variable "app_name" {
  description = "Name of the application"
  type        = string
}

variable "app_service_sku_name_api" {
  description = "SKU name for the API App Service Plan"
  type        = string
  default     = "B1" # Basic tier 
}

variable "client_id" {
  description = "Azure client ID for the service principal"
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
}

variable "cosmosdb_container_name" {
  description = "Name of the CosmosDB container"
  type        = string
  sensitive   = true
}

variable "cosmosdb_db_name" {
  description = "Name of the CosmosDB database"
  type        = string
}

variable "cosmosdb_endpoint" {
  description = "Endpoint URI for the CosmosDB account"
  type        = string
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

variable "frontdoor_sku_name" {
  description = "SKU name for the Front Door"
  type        = string
  default     = "Standard_AzureFrontDoor"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "Canada Central"
}

variable "log_analytics_retention_days" {
  description = "Number of days to retain data in Log Analytics Workspace"
  type        = number
  default     = 30
}

variable "log_analytics_sku" {
  description = "SKU for Log Analytics Workspace"
  type        = string
  default     = "PerGB2018"
}

variable "repo_name" {
  description = "Name of the repository, used for resource naming"
  type        = string
  default     = "quickstart-azure-containers"
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
  sensitive   = true
}

variable "tenant_id" {
  description = "Azure tenant ID"
  type        = string
  sensitive   = true
}

variable "use_oidc" {
  description = "Use OIDC for authentication"
  type        = bool
  default     = true
}

variable "vnet_address_space" {
  type        = string
  description = "Address space for the virtual network, it is created by platform team"
}

variable "vnet_name" {
  description = "Name of the existing virtual network"
  type        = string
}

variable "vnet_resource_group_name" {
  description = "Resource group name where the virtual network exists"
  type        = string
}
