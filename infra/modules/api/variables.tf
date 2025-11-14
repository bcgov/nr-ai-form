variable "api_frontdoor_firewall_policy_id" {
  description = "The resource ID of the Front Door firewall policy for the API."
  type        = string
  nullable    = false
}

variable "api_frontdoor_id" {
  description = "The resource ID of the Front Door profile for the API."
  type        = string
  nullable    = false
}

variable "api_frontdoor_resource_guid" {
  description = "The resource GUID for the Front Door service associated with the API App Service."
  type        = string
  nullable    = false
}

variable "api_image" {
  description = "The Docker image for the backend API."
  type        = string
  nullable    = false
}

variable "app_env" {
  description = "The deployment environment (e.g., dev, test, prod)."
  type        = string
  nullable    = false
}

variable "app_name" {
  description = "The base name of the application. Used for naming Azure resources."
  type        = string
  nullable    = false
}

variable "app_service_sku_name_api" {
  description = "The SKU name for the API App Service plan."
  type        = string
  nullable    = false
}

variable "app_service_subnet_id" {
  description = "The subnet ID for the App Service."
  type        = string
  nullable    = false
}

variable "appinsights_connection_string" {
  description = "The Application Insights connection string for monitoring."
  type        = string
  nullable    = false
}

variable "appinsights_instrumentation_key" {
  description = "The Application Insights instrumentation key."
  type        = string
  nullable    = false
}

variable "backend_autoscale_enabled" {
  description = "Whether autoscaling is enabled for the backend App Service plan."
  type        = bool
  default     = true
}

variable "backend_depends_on" {
  description = "A list of resources this backend depends on."
  type        = list(any)
  default     = []
}


variable "common_tags" {
  description = "A map of tags to apply to resources."
  type        = map(string)
  default     = {}
}

variable "container_registry_url" {
  description = "The URL of the container registry to pull images from."
  type        = string
  nullable    = false
  default     = "https://ghcr.io"
}

variable "cosmosdb_container_name" {
  description = "The name of the Cosmos DB container."
  type        = string
  nullable    = false
}

variable "cosmosdb_db_name" {
  description = "The name of the Cosmos DB database."
  type        = string
  nullable    = false
}

variable "cosmosdb_endpoint" {
  description = "The endpoint URI for the Azure Cosmos DB account."
  type        = string
  nullable    = false
}



variable "location" {
  description = "The Azure region where resources will be created."
  type        = string
  nullable    = false
}

variable "log_analytics_workspace_id" {
  description = "The resource ID of the Log Analytics workspace for diagnostics."
  type        = string
  nullable    = false
}

variable "private_endpoint_subnet_id" {
  description = "The subnet ID for private endpoints."
  type        = string
  nullable    = false
}

variable "repo_name" {
  description = "The repository name, used for resource naming."
  type        = string
  nullable    = false
}

variable "resource_group_name" {
  description = "The name of the resource group in which to create resources."
  type        = string
  nullable    = false
}

variable "azure_openai_api_key" {
  description = "The API key for Azure OpenAI service."
  type        = string
  sensitive   = true
  nullable    = false
}

variable "azure_openai_endpoint" {
  description = "The endpoint URL for Azure OpenAI service."
  type        = string
  nullable    = false
}

variable "azure_openai_api_version" {
  description = "The API version for Azure OpenAI service."
  type        = string
  default     = "2024-10-21"
  nullable    = false
}

variable "azure_openai_deployment_name" {
  description = "The deployment name for Azure OpenAI model."
  type        = string
  nullable    = false
}

