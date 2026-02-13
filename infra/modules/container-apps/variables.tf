# Container Apps Module Variables - NR AI Form Backend

variable "app_env" {
  description = "Application environment (dev, test, prod)"
  type        = string
  nullable    = false
}

variable "app_name" {
  description = "Name of the application"
  type        = string
  nullable    = false
}

variable "repo_name" {
  description = "Name of the repository"
  type        = string
  nullable    = false
}

variable "appinsights_connection_string" {
  description = "Application Insights connection string"
  type        = string
  sensitive   = true
  nullable    = false
}

variable "appinsights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  type        = string
  sensitive   = true
  nullable    = false
}

variable "azure_document_intelligence_endpoint" {
  description = "Azure Document Intelligence endpoint"
  type        = string
  nullable    = false
}

variable "azure_document_intelligence_key" {
  description = "Azure Document Intelligence API key"
  type        = string
  sensitive   = true
  nullable    = false
}

variable "azure_openai_api_key" {
  description = "Azure OpenAI API key"
  type        = string
  sensitive   = true
  nullable    = false
}

variable "azure_openai_api_version" {
  description = "Azure OpenAI API version"
  type        = string
  default     = "2024-02-01"
  nullable    = false
}

variable "azure_openai_deployment_name" {
  description = "Azure OpenAI deployment name"
  type        = string
  nullable    = false
}

variable "azure_openai_endpoint" {
  description = "Azure OpenAI endpoint"
  type        = string
  nullable    = false
}

variable "azure_search_endpoint" {
  description = "Azure Search endpoint"
  type        = string
  nullable    = false
}

variable "azure_search_index_name" {
  description = "Azure Search index name"
  type        = string
  nullable    = false
}

variable "azure_search_key" {
  description = "Azure Search API key"
  type        = string
  sensitive   = true
  nullable    = false
}

variable "azure_storage_account_key" {
  description = "Azure Storage account key"
  type        = string
  sensitive   = true
  nullable    = false
}

variable "azure_storage_account_name" {
  description = "Azure Storage account name"
  type        = string
  nullable    = false
}

variable "azure_storage_container_name" {
  description = "Azure Storage container name"
  type        = string
  nullable    = false
}

variable "backend_image" {
  description = "Container image for the backend API (deprecated - use orchestrator_agent_image)"
  type        = string
  default     = ""
  nullable    = false
}

variable "orchestrator_agent_image" {
  description = "Container image for the Orchestrator Agent"
  type        = string
  default     = ""
  nullable    = true
}

variable "conversation_agent_image" {
  description = "Container image for the Conversation Agent"
  type        = string
  default     = ""
  nullable    = true
}

variable "formsupport_agent_image" {
  description = "Container image for the Form Support Agent"
  type        = string
  default     = ""
  nullable    = true
}

variable "orchestrator_agent_port" {
  description = "Port for the Orchestrator Agent"
  type        = number
  default     = 8002
  nullable    = false
}

variable "conversation_agent_port" {
  description = "Port for the Conversation Agent"
  type        = number
  default     = 8000
  nullable    = false
}

variable "formsupport_agent_port" {
  description = "Port for the Form Support Agent"
  type        = number
  default     = 8001
  nullable    = false
}

variable "container_registry_url" {
  description = "Container registry URL for image pulls"
  type        = string
  default     = "https://ghcr.io"
  nullable    = false
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  nullable    = false
}

variable "container_apps_subnet_id" {
  description = "Subnet ID for Container Apps Environment"
  type        = string
  nullable    = false
}

variable "container_cpu" {
  description = "CPU allocation for backend container app (in cores)"
  type        = number
  default     = 0.5
  nullable    = false
}

variable "container_memory" {
  description = "Memory allocation for backend container app"
  type        = string
  default     = "1Gi"
  nullable    = false
}

variable "cosmosdb_container_name" {
  description = "Cosmos DB container name"
  type        = string
  nullable    = false
}

variable "cosmosdb_db_name" {
  description = "Cosmos DB database name"
  type        = string
  nullable    = false
}

variable "cosmosdb_endpoint" {
  description = "Cosmos DB endpoint"
  type        = string
  nullable    = false
}

variable "enable_system_assigned_identity" {
  description = "Enable system assigned managed identity"
  type        = bool
  default     = true
  nullable    = false
}

variable "location" {
  description = "Azure region where resources will be deployed"
  type        = string
  nullable    = false
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID for Container Apps Environment"
  type        = string
  nullable    = false
}

variable "log_level" {
  description = "Log level for the application"
  type        = string
  default     = "INFO"
  nullable    = false
}

# Front Door Integration
variable "api_frontdoor_id" {
  description = "Front Door Profile ID for API integration"
  type        = string
  nullable    = false
}

variable "api_frontdoor_resource_guid" {
  description = "Front Door Resource GUID for header validation"
  type        = string
  nullable    = false
}

variable "api_frontdoor_firewall_policy_id" {
  description = "Front Door Firewall Policy ID for API protection"
  type        = string
  nullable    = false
}

variable "max_replicas" {
  description = "Maximum number of replicas for backend"
  type        = number
  default     = 10 # Higher max for Consumption workload
  nullable    = false
}

variable "min_replicas" {
  description = "Minimum number of replicas for backend"
  type        = number
  default     = 0 # Allow scale to zero for Consumption workload
  nullable    = false
}

variable "private_endpoint_subnet_id" {
  description = "Subnet ID for the private endpoint"
  type        = string
  nullable    = false
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  nullable    = false
}
