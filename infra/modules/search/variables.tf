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

variable "search_sku" {
  description = "Azure AI Search SKU (basic, standard, standard2, standard3, ...). Semantic ranking requires basic or higher."
  type        = string
  default     = "standard"
}

variable "semantic_search_sku" {
  description = "Semantic ranker plan (free or standard). Needed because the agent queries with query_type = semantic."
  type        = string
  default     = "standard"
}

variable "replica_count" {
  description = "Number of search replicas. 2+ gives a read SLA, 3+ gives a read/write SLA."
  type        = number
  default     = 2
}

variable "partition_count" {
  description = "Number of search partitions."
  type        = number
  default     = 1
}

variable "public_network_access_enabled" {
  description = "Allow public access to the search endpoint. Keep false in prod; the Container App reaches it through the private endpoint."
  type        = bool
  default     = false
}
