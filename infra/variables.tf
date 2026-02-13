# -------------
# Root Variables for Azure Infrastructure
# -------------

variable "deployment_type" {
  description = "Type of deployment: 'app_service' or 'container_apps'"
  type        = string
  default     = "app_service" # Default to App Service for backwards compatibility

  validation {
    condition     = contains(["app_service", "container_apps"], var.deployment_type)
    error_message = "deployment_type must be either 'app_service' or 'container_apps'"
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

variable "app_service_sku_name_api" {
  description = "SKU name for the API App Service Plan. Must be Standard or higher for sidecar support (e.g., S1, S2, P1)"
  type        = string
  default     = "S1" # Standard tier - required for sidecar containers
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

variable "dev_app_service_subnet_id" {
  description = "The subnet ID for app service in dev environment"
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

variable "azure_openai_deployment_name" {
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

variable "azure_search_key" {
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

