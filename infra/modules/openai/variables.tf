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
  description = "Azure region for the Azure OpenAI account (must offer the embedding model with embedding_sku_name)."
  type        = string
  nullable    = false
}

variable "private_endpoint_location" {
  description = "Azure region of the private endpoint; must match the VNet of private_endpoint_subnet_id."
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

variable "search_service_id" {
  description = "The ID of the Azure AI Search service that calls the embedding model (shared private link source)."
  type        = string
  nullable    = false
}

variable "search_principal_id" {
  description = "Principal ID of the Azure AI Search system-assigned identity; granted Cognitive Services OpenAI User."
  type        = string
  nullable    = false
}

variable "embedding_deployment_name" {
  description = "Name of the text-embedding-3-large deployment (referenced by the Search vectorizer / skillset)."
  type        = string
  default     = "text-embedding-3-large"
}

variable "embedding_model_version" {
  description = "Version of the text-embedding-3-large model."
  type        = string
  default     = "1"
}

variable "embedding_sku_name" {
  description = "Deployment SKU. Canada Central only offers GlobalStandard for text-embedding-3-large (Canada East also offers Standard)."
  type        = string
  default     = "GlobalStandard"
}

variable "embedding_capacity" {
  description = "Deployment capacity in thousands of tokens per minute (TPM)."
  type        = number
  default     = 150
}

variable "public_network_access_enabled" {
  description = "Allow public access to the Azure OpenAI endpoint. Keep false in prod; Search uses the shared private link and the Container Apps the private endpoint."
  type        = bool
  default     = false
}

variable "local_auth_enabled" {
  description = "Allow API key authentication. Search uses its managed identity, so keys are disabled by default."
  type        = bool
  default     = false
}
