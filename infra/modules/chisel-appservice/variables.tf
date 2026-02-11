variable "app_service_name" {
  description = "Name of the App Service"
  type        = string
  default     = "chisel-proxy"
}

variable "app_service_plan_name" {
  description = "Name of the App Service Plan"
  type        = string
  default     = "chisel-proxy-plan"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "sku_name" {
  description = "App Service Plan SKU (e.g., B1, B2, P1V2, etc.)"
  type        = string
  default     = "B2"

  validation {
    condition     = can(regex("^(B|P|S|D|F)[0-9]V?[0-9]?$", var.sku_name))
    error_message = "SKU must be a valid Azure App Service SKU (e.g., B1, B2, P1V2, etc.)"
  }
}

variable "docker_image_name" {
  description = "Docker image name including tag (format: repository/image:tag)"
  type        = string
  # Example: "nr-ai-form-chisel:latest"
}

variable "registry_server" {
  description = "Docker registry server (e.g., myacr.azurecr.io)"
  type        = string
}

variable "registry_username" {
  description = "Docker registry username"
  type        = string
  sensitive   = true
}

variable "registry_password" {
  description = "Docker registry password"
  type        = string
  sensitive   = true
}

variable "chisel_password" {
  description = "Chisel authentication password"
  type        = string
  sensitive   = true
}

variable "chisel_port" {
  description = "Port for Chisel to listen on"
  type        = string
  default     = "8080"
}

variable "chisel_host" {
  description = "Host address to bind to"
  type        = string
  default     = "0.0.0.0"
}

variable "enable_socks5" {
  description = "Enable SOCKS5 proxy support"
  type        = bool
  default     = true
}

variable "max_retries" {
  description = "Maximum retry attempts"
  type        = string
  default     = "30"
}

variable "delay_seconds" {
  description = "Delay in seconds between retries"
  type        = string
  default     = "5"
}

variable "health_check_path" {
  description = "Health check path"
  type        = string
  default     = "/"
}

variable "min_instances" {
  description = "Minimum number of App Service instances"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of App Service instances"
  type        = number
  default     = 3
}

variable "enable_autoscale" {
  description = "Enable auto-scaling based on CPU percentage"
  type        = bool
  default     = true
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID for diagnostics"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
