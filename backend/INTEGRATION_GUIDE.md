# Integration Guide: BC Government Terraform Infrastructure

This document outlines the required changes to integrate the AI Agent with the existing BC Government Terraform infrastructure at https://github.com/bcgov/nr-ai-form/tree/master/infra.

## Overview

The AI Agent application is designed to work with the existing BC Government infrastructure pattern using:
- **GitHub Container Registry** for Docker images
- **GitHub Secrets** for sensitive information
- **Terraform** for infrastructure as code
- **Azure Container Apps** for hosting

## Required GitHub Secrets

Add these secrets to your GitHub repository settings:

### Azure Authentication
```
AZURE_CREDENTIALS          # Service Principal JSON for Terraform
TF_STATE_STORAGE_ACCOUNT   # Storage account for Terraform state
TF_STATE_CONTAINER         # Container name for Terraform state
TF_STATE_RESOURCE_GROUP    # Resource group for Terraform state
```

### Development Environment
```
AZURE_OPENAI_API_KEY              # Azure OpenAI API key for dev
AZURE_OPENAI_ENDPOINT             # Azure OpenAI endpoint for dev
AZURE_OPENAI_DEPLOYMENT_NAME      # Model deployment name for dev
```

### Production Environment
```
AZURE_OPENAI_API_KEY_PROD         # Azure OpenAI API key for prod
AZURE_OPENAI_ENDPOINT_PROD        # Azure OpenAI endpoint for prod
AZURE_OPENAI_DEPLOYMENT_NAME_PROD # Model deployment name for prod
```

## Required Terraform Updates

### 1. Update `variables.tf`

Add these variables to your existing `infra/variables.tf`:

```hcl
# Docker image for the AI Agent
variable "docker_image" {
  description = "Docker image for the AI Agent container"
  type        = string
  default     = "ghcr.io/your-org/ai-agent:latest"
}

# Azure OpenAI Configuration
variable "azure_openai_api_key" {
  description = "Azure OpenAI API Key"
  type        = string
  sensitive   = true
}

variable "azure_openai_endpoint" {
  description = "Azure OpenAI Endpoint"
  type        = string
}

variable "azure_openai_api_version" {
  description = "Azure OpenAI API Version"
  type        = string
  default     = "2025-01-01-preview"
}

variable "azure_openai_deployment_name" {
  description = "Azure OpenAI Deployment Name"
  type        = string
  default     = "gpt-4o-mini"
}

# Container App Configuration
variable "container_port" {
  description = "Port on which the container listens"
  type        = number
  default     = 8000
}

variable "cpu_limit" {
  description = "CPU limit for the container"
  type        = string
  default     = "0.5"
}

variable "memory_limit" {
  description = "Memory limit for the container"
  type        = string
  default     = "1Gi"
}

variable "min_replicas" {
  description = "Minimum number of replicas"
  type        = number
  default     = 1
}

variable "max_replicas" {
  description = "Maximum number of replicas"
  type        = number
  default     = 3
}
```

### 2. Update Container App Configuration

In your existing Container App resource, update the configuration:

```hcl
resource "azurerm_container_app" "ai_agent" {
  name                         = "${local.project_name}-${var.environment}-ca"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.common_tags

  # Registry configuration for GitHub Container Registry
  registry {
    server   = "ghcr.io"
    username = var.github_username  # Add as variable
    password = var.github_token     # Add as variable or use managed identity
  }

  template {
    min_replicas = var.min_replicas
    max_replicas = var.max_replicas

    container {
      name   = "ai-agent"
      image  = var.docker_image
      cpu    = var.cpu_limit
      memory = var.memory_limit

      # Environment variables
      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = var.azure_openai_endpoint
      }

      env {
        name  = "AZURE_OPENAI_API_VERSION"
        value = var.azure_openai_api_version
      }

      env {
        name  = "AZURE_OPENAI_DEPLOYMENT_NAME"
        value = var.azure_openai_deployment_name
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "DEBUG"
        value = var.environment == "prod" ? "false" : "true"
      }

      env {
        name  = "PORT"
        value = var.container_port
      }

      # Sensitive environment variables from secrets
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-api-key"
      }
    }
  }

  # Secret configuration
  secret {
    name  = "azure-openai-api-key"
    value = var.azure_openai_api_key
  }

  # Ingress configuration
  ingress {
    external_enabled = true
    target_port      = var.container_port

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}
```

### 3. Add Output Values

Add these outputs to your `outputs.tf`:

```hcl
output "ai_agent_url" {
  description = "URL of the AI Agent application"
  value       = "https://${azurerm_container_backend.ai_agent.latest_revision_fqdn}"
}

output "ai_agent_fqdn" {
  description = "FQDN of the AI Agent application"
  value       = azurerm_container_backend.ai_agent.latest_revision_fqdn
}
```

### 4. Environment-Specific tfvars Files

Create environment-specific variable files:

**`terraform.dev.tfvars`:**
```hcl
environment = "dev"
min_replicas = 1
max_replicas = 3
cpu_limit = "0.5"
memory_limit = "1Gi"
```

**`terraform.prod.tfvars`:**
```hcl
environment = "prod"
min_replicas = 2
max_replicas = 10
cpu_limit = "1.0"
memory_limit = "2Gi"
```

## Integration Steps

### 1. Update Your Repository

1. Copy the `Dockerfile` to your repository root
2. Copy the `.github/workflows/deploy.yml` to your repository
3. Update the workflow file with your specific repository and organization details

### 2. Configure GitHub Secrets

In your GitHub repository settings, add all the required secrets listed above.

### 3. Update Terraform Files

Apply the Terraform changes outlined above to your existing infrastructure code.

### 4. Test the Integration

1. Push changes to your main branch
2. The GitHub Action will automatically:
   - Build the Docker image
   - Push to GitHub Container Registry
   - Deploy using Terraform
   - Perform health checks

## Security Best Practices

### 1. Secret Management
- **Never commit secrets** to version control
- Use **GitHub Secrets** for all sensitive information
- Secrets are injected as environment variables during deployment
- Use different secrets for different environments

### 2. Container Security
- Base image uses **non-root user**
- **Multi-stage build** for smaller attack surface
- **Health checks** for availability monitoring
- **Distroless or minimal** base images recommended

### 3. Azure Integration
- Use **Managed Identity** where possible
- **Network security groups** for access control
- **Application Insights** for monitoring
- **Azure Key Vault** as an additional layer (optional)

## Monitoring and Observability

### Application Insights Integration
Add Application Insights configuration to your Container App:

```hcl
env {
  name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
  value = azurerm_application_insights.main.connection_string
}
```

### Log Analytics
The Container App Environment should be connected to Log Analytics workspace for centralized logging.

## Scaling Configuration

The application supports horizontal scaling based on:
- **CPU usage**
- **Memory usage**
- **HTTP request count**
- **Custom metrics**

Configure auto-scaling rules in your Terraform:

```hcl
resource "azurerm_monitor_autoscale_setting" "ai_agent" {
  name                = "${local.project_name}-${var.environment}-autoscale"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  target_resource_id  = azurerm_container_backend.ai_agent.id

  profile {
    name = "default"

    capacity {
      default = var.min_replicas
      minimum = var.min_replicas
      maximum = var.max_replicas
    }

    rule {
      metric_trigger {
        metric_name        = "CpuPercentage"
        metric_resource_id = azurerm_container_backend.ai_agent.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT5M"
        time_aggregation   = "Average"
        operator           = "GreaterThan"
        threshold          = 70
      }

      scale_action {
        direction = "Increase"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT5M"
      }
    }
  }
}
```

This integration provides a secure, scalable, and maintainable deployment pipeline following BC Government standards.
