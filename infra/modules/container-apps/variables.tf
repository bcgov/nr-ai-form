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

variable "branch_slug" {
  description = "URL-safe slug of the deploying branch. Appended to the Container App name so each branch gets its own ACA in dev."
  type        = string
  default     = "master"
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

variable "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME" {
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

variable "AZURE_SEARCH_API_KEY" {
  description = "Azure Search API key"
  type        = string
  sensitive   = true
  nullable    = false
}

variable "azure_search_top" {
  description = "Number of top search results to return"
  type        = number
  default     = 10
  nullable    = false
}

variable "azure_search_trim_length" {
  description = "Maximum character length to trim search result content"
  type        = number
  default     = 1000
  nullable    = false
}

variable "azure_search_enable_trimming" {
  description = "Whether to enable trimming of search result content"
  type        = bool
  default     = false
  nullable    = false
}

# Extended Azure Search Configuration Variables
variable "azure_search_include_total_count" {
  description = "Include total count of search results"
  type        = bool
  default     = true
  nullable    = false
}

variable "azure_search_query_type" {
  description = "Type of Azure Search query (simple, semantic, full)"
  type        = string
  default     = "semantic"
  nullable    = false
}

variable "azure_search_semantic_configuration" {
  description = "Semantic search configuration name"
  type        = string
  default     = "semanticconfig"
  nullable    = false
}

variable "azure_search_query_caption" {
  description = "Caption extraction method for search results"
  type        = string
  default     = "extractive"
  nullable    = false
}

variable "azure_search_query_answer" {
  description = "Answer extraction method for search results"
  type        = string
  default     = "extractive"
  nullable    = false
}

variable "azure_search_query_answer_count" {
  description = "Number of answers to extract from search results"
  type        = number
  default     = 3
  nullable    = false
}

variable "azure_search_query_language" {
  description = "Language for semantic search configuration"
  type        = string
  default     = "en-us"
  nullable    = false
}

# LLM Agent Configuration Variables
variable "agent_temperature" {
  description = "Temperature parameter for LLM responses (0.0-2.0, lower is more deterministic)"
  type        = number
  default     = 0.1
  nullable    = false

  validation {
    condition     = var.agent_temperature >= 0.0 && var.agent_temperature <= 2.0
    error_message = "agent_temperature must be between 0.0 and 2.0"
  }
}

variable "agent_max_tokens" {
  description = "Maximum tokens allowed in LLM response"
  type        = number
  default     = 800
  nullable    = false

  validation {
    condition     = var.agent_max_tokens >= 1 && var.agent_max_tokens <= 4096
    error_message = "agent_max_tokens must be between 1 and 4096"
  }
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

variable "azure_blobstorage_connectionstring" {
  description = "Azure Blob Storage connection string"
  type        = string
  sensitive   = true
  nullable    = false
}

variable "azure_blobstorage_container" {
  description = "Azure Blob Storage container name"
  type        = string
  nullable    = false
}

# Redis Configuration
variable "redis_host" {
  description = "Redis cache hostname"
  type        = string
  default     = ""
  nullable    = false
}

variable "redis_port" {
  description = "Redis cache port"
  type        = number
  default     = 10000
  nullable    = false
}

variable "redis_password" {
  description = "Redis cache access key"
  type        = string
  sensitive   = true
  default     = ""
  nullable    = false
}

variable "redis_ssl" {
  description = "Whether to use SSL for Redis connections"
  type        = bool
  default     = true
  nullable    = false
}

variable "redis_ttl_days" {
  description = "TTL in days for Redis cache entries"
  type        = number
  default     = 14
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

/*
variable "api_backend_image" {
  description = "Container image for the API Backend (WebSocket gateway between frontend and orchestrator)"
  type        = string
  default     = ""
  nullable    = false
}

variable "api_backend_port" {
  description = "Port for the API Backend"
  type        = number
  default     = 8003
  nullable    = false
}
*/

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
  description = "Subnet ID for Container Apps Environment. Empty string or null means no dedicated subnet (dev without a pre-created subnet)."
  type        = string
  default     = ""
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
variable "enable_front_door" {
  description = "Whether Front Door is enabled for this environment. When false, all CDN/Front Door resources are skipped."
  type        = bool
  default     = true
  nullable    = false
}

variable "api_frontdoor_id" {
  description = "Front Door Profile ID for API integration"
  type        = string
  default     = ""
  nullable    = false
}

variable "api_frontdoor_resource_guid" {
  description = "Front Door Resource GUID for header validation"
  type        = string
  default     = ""
  nullable    = false
}

variable "api_frontdoor_firewall_policy_id" {
  description = "Front Door Firewall Policy ID for API protection"
  type        = string
  default     = ""
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

variable "internal_load_balancer_enabled" {
  description = "Whether to use an internal load balancer for the Container App Environment"
  type        = bool
  default     = false
  nullable    = false
}
