# -------------
# Root Variables for Azure Infrastructure
# -------------

variable "branch_slug" {
  description = "URL-safe slug of the deploying branch. Appended to the Container App name in dev so each branch gets its own ACA. Defaults to 'master'."
  type        = string
  default     = "master"
}

variable "deployment_type" {
  description = "Type of deployment: 'container_apps'"
  type        = string
  default     = "container_apps"

  validation {
    condition     = var.deployment_type == "container_apps"
    error_message = "deployment_type must be 'container_apps'. App Service deployment is no longer supported."
  }
}

variable "conversation_agent_image" {
  description = "The image for the conversation agent container"
  type        = string
}

variable "formsupport_agent_image" {
  description = "The image for the form support agent container"
  type        = string
}

variable "orchestrator_agent_image" {
  description = "The image for the orchestrator agent container"
  type        = string
}

/*
variable "api_backend_image" {
  description = "The image for the API Backend container (WebSocket gateway)"
  type        = string
  default     = ""
}
*/

# Legacy variable for Container Apps compatibility - will use conversation_agent_image
variable "api_image" {
  description = "The image for the API container (used by Container Apps - defaults to conversation_agent_image)"
  type        = string
  default     = ""
}

variable "app_env" {
  description = "Application environment (dev, test, prod)"
  type        = string
  default     = "test"
}

variable "app_name" {
  description = "Name of the application"
  type        = string
}

variable "container_cpu" {
  description = "CPU allocation for backend container app (in cores)"
  type        = number
  default     = 0.5
}

variable "container_memory" {
  description = "Memory allocation for backend container app"
  type        = string
  default     = "1Gi"
}

variable "min_replicas" {
  description = "Minimum number of replicas for backend container app"
  type        = number
  default     = 0 # Allow scale to zero for cost optimization
}

variable "max_replicas" {
  description = "Maximum number of replicas for backend container app"
  type        = number
  default     = 10
}

variable "client_id" {
  description = "Azure client ID for the service principal"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
}



variable "enable_front_door" {
  description = "Whether to deploy and connect Front Door. Set to false for environments that do not use Front Door (e.g. dev)."
  type        = bool
  default     = true
}

variable "frontdoor_sku_name" {
  description = "SKU name for the Front Door"
  type        = string
  default     = "Premium_AzureFrontDoor"
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
  nullable    = false
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

variable "dev_private_endpoint_subnet_id" {
  description = "The subnet ID for private endpoints in dev environment"
  type        = string
  default     = ""
}

variable "dev_container_apps_subnet_id" {
  description = "The subnet ID for container apps in dev environment (must be dedicated and empty)"
  type        = string
  default     = ""
}

# Azure OpenAI Configuration
variable "azure_openai_api_key" {
  description = "The API key for Azure OpenAI service. This will be passed as an environment variable to the backend application."
  type        = string
  sensitive   = true
  nullable    = false
}

variable "azure_openai_endpoint" {
  description = "The endpoint URL for Azure OpenAI service (e.g., https://your-resource.openai.azure.com)."
  type        = string
  nullable    = false
}

variable "azure_openai_api_version" {
  description = "The API version for Azure OpenAI service."
  type        = string
  default     = "2024-10-21"
  nullable    = false
}

variable "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME" {
  description = "The deployment name for the Azure OpenAI model."
  type        = string
  nullable    = false
}

# Azure Search Configuration
variable "azure_search_endpoint" {
  description = "The endpoint URL for Azure AI Search service."
  type        = string
  nullable    = false
}

variable "AZURE_SEARCH_API_KEY" {
  description = "The API key for Azure AI Search service."
  type        = string
  sensitive   = true
  nullable    = false
}

variable "azure_search_index_name" {
  description = "The index name for Azure AI Search service."
  type        = string
  nullable    = false
}

variable "azure_search_top" {
  description = "Number of top search results to return (passed to conversation agent)."
  type        = number
  default     = 10
}

variable "azure_search_trim_length" {
  description = "Maximum character length to trim search result content (passed to conversation agent)."
  type        = number
  default     = 1000
}

variable "azure_search_enable_trimming" {
  description = "Whether to enable trimming of search result content (passed to conversation agent)."
  type        = bool
  default     = false
}

variable "azure_search_include_total_count" {
  description = "Whether to include total count of search results. Defaults to true."
  type        = bool
  default     = true
}

variable "azure_search_query_type" {
  description = "Type of search query (e.g., 'simple', 'semantic'). Defaults to 'semantic'."
  type        = string
  default     = "semantic"
}

variable "azure_search_semantic_configuration" {
  description = "Name of the semantic configuration to use. Defaults to 'semanticconfig'."
  type        = string
  default     = "semanticconfig"
}

variable "azure_search_query_caption" {
  description = "Caption extraction method for search results (e.g., 'extractive', 'generative'). Defaults to 'extractive'."
  type        = string
  default     = "extractive"
}

variable "azure_search_query_answer" {
  description = "Answer extraction method for search results (e.g., 'extractive', 'generative'). Defaults to 'extractive'."
  type        = string
  default     = "extractive"
}

variable "azure_search_query_answer_count" {
  description = "Number of answers to extract from search results. Defaults to 3."
  type        = number
  default     = 3
}

variable "azure_search_query_language" {
  description = "Language code for semantic search queries (e.g., 'en-us'). Defaults to 'en-us'."
  type        = string
  default     = "en-us"
}

variable "agent_temperature" {
  description = "Temperature for LLM responses (0.0-2.0). Lower = more deterministic, higher = more creative. Defaults to 0.1."
  type        = number
  default     = 0.1

  validation {
    condition     = var.agent_temperature >= 0.0 && var.agent_temperature <= 2.0
    error_message = "agent_temperature must be between 0.0 and 2.0."
  }
}

variable "agent_max_tokens" {
  description = "Maximum number of tokens in LLM responses. Defaults to 800."
  type        = number
  default     = 800

  validation {
    condition     = var.agent_max_tokens > 0 && var.agent_max_tokens <= 4096
    error_message = "agent_max_tokens must be between 1 and 4096."
  }
}

# Azure Document Intelligence Configuration
variable "azure_document_intelligence_endpoint" {
  description = "The endpoint URL for Azure Document Intelligence service."
  type        = string
  nullable    = false
}

variable "azure_document_intelligence_key" {
  description = "The API key for Azure Document Intelligence service."
  type        = string
  sensitive   = true
  nullable    = false
}

# Azure Storage Configuration
variable "azure_storage_account_name" {
  description = "The name of the Azure Storage account."
  type        = string
  nullable    = false
}

variable "azure_storage_account_key" {
  description = "The access key for the Azure Storage account."
  type        = string
  sensitive   = true
  nullable    = false
}

variable "azure_storage_container_name" {
  description = "The container name in Azure Storage for document storage."
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
}

variable "redis_port" {
  description = "Redis cache port"
  type        = number
  default     = 10000
}

variable "redis_password" {
  description = "Redis cache access key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "redis_ssl" {
  description = "Whether to use SSL for Redis connections"
  type        = bool
  default     = true
}

variable "redis_ttl_days" {
  description = "TTL in days for Redis cache entries"
  type        = number
  default     = 14
}

# Sidecar Deployment Configuration
variable "orchestrator_agent_port" {
  description = "The port on which the Orchestrator Agent (main container) listens."
  type        = number
  default     = 8002
}

variable "conversation_agent_port" {
  description = "The port on which the Conversation Agent (sidecar) listens."
  type        = number
  default     = 8000
}

variable "formsupport_agent_port" {
  description = "The port on which the Form Support Agent (sidecar) listens."
  type        = number
  default     = 8001
}

variable "container_registry_url" {
  description = "The URL of the container registry for pulling sidecar images."
  type        = string
  default     = ""
}

variable "container_registry_username" {
  description = "The username for authenticating with the container registry."
  type        = string
  default     = ""
  sensitive   = true
}

variable "container_registry_password" {
  description = "The password/token for authenticating with the container registry."
  type        = string
  default     = ""
  sensitive   = true
}

variable "cors_allow_origins" {
  description = "List of allowed origins for CORS (e.g., ['https://example.com'])."
  type        = list(string)
  default     = []
}
