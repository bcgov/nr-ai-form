variable "app_name" {
  type        = string
  description = "Application name"
}

variable "environment" {
  type        = string
  description = "Environment (dev, test, prod)"
}

variable "location" {
  type        = string
  description = "Azure region"
}

variable "resource_group_name" {
  type        = string
  description = "Resource group name"
}

variable "chisel_server_auth" {
  type        = string
  description = "Chisel server authentication (format: user:password)"
  sensitive   = true
}

variable "common_tags" {
  type        = map(string)
  description = "Common tags for all resources"
  default     = {}
}
