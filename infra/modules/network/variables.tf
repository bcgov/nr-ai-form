variable "apps_service_subnet_name" {
  description = "Name of the subnet for App Services"
  type        = string
  default     = "app-service-subnet"
  nullable    = false
}

variable "deploy_network" {
  description = "Flag to control whether to deploy network resources. Set to false for dev environment."
  type        = bool
  default     = true
}

variable "app_env" {
  description = "Application environment (dev, test, prod)"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  nullable    = false
}


variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "Canada Central"
  nullable    = false
}

variable "private_endpoint_subnet_name" {
  description = "Name of the subnet for private endpoints"
  type        = string
  default     = "privateendpoints-subnet"
  nullable    = false
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  nullable    = false
}

variable "vnet_address_space" {
  type        = string
  description = "Address space for the virtual network, it is created by platform team"
  nullable    = false
}

variable "vnet_name" {
  description = "Name of the existing virtual network"
  type        = string
  nullable    = false
}

variable "vnet_resource_group_name" {
  description = "Resource group name where the virtual network exists"
  type        = string
  nullable    = false
}
