# Environment Configuration for Azure Deployment
# This file should be used as a reference for setting up environment variables

# =============================================================================
# DEVELOPMENT ENVIRONMENT (.env file)
# =============================================================================
# Copy this section to .env for local development

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_dev_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-dev-openai.openai.azure.com
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini

# Local tunnel settings (for private DNS resolution)
USE_LOCAL_TUNNEL=true
LOCAL_TUNNEL_PORT=8082
LOCAL_TUNNEL_HOST=localhost
TUNNEL_RESOLVE_HOST=css-ai-dev-openai-east.openai.azure.com

# Server settings
HOST=0.0.0.0
PORT=8000
DEBUG=true
ALLOWED_HOSTS=*

# =============================================================================
# AZURE APP SERVICE ENVIRONMENT VARIABLES
# =============================================================================
# These should be set in Azure App Service Configuration -> Application Settings
# DO NOT set AZURE_OPENAI_API_KEY directly - it should come from GitHub Secrets

# Required settings (set through GitHub Actions from secrets)
AZURE_OPENAI_ENDPOINT=https://your-openai-service.openai.azure.com
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini

# Environment identification
ENVIRONMENT=prod  # or dev, test

# Server configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
ALLOWED_HOSTS=*

# Disable local tunnel in production
USE_LOCAL_TUNNEL=false

# =============================================================================
# GITHUB SECRETS CONFIGURATION
# =============================================================================
# Add these secrets to your GitHub repository

# Azure Service Principal for Terraform
AZURE_CREDENTIALS={
  "clientId": "your-client-id",
  "clientSecret": "your-client-secret",
  "subscriptionId": "your-subscription-id",
  "tenantId": "your-tenant-id"
}

# Terraform State Storage
TF_STATE_STORAGE_ACCOUNT=your_terraform_storage_account
TF_STATE_CONTAINER=tfstate
TF_STATE_RESOURCE_GROUP=your_terraform_rg

# Development Environment Secrets
AZURE_OPENAI_API_KEY=your_dev_api_key
AZURE_OPENAI_ENDPOINT=https://your-dev-openai.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini

# Production Environment Secrets
AZURE_OPENAI_API_KEY_PROD=your_prod_api_key
AZURE_OPENAI_ENDPOINT_PROD=https://your-prod-openai.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME_PROD=gpt-4o-mini

# =============================================================================
# TERRAFORM VARIABLES
# =============================================================================
# These variables should be passed to Terraform via GitHub Actions

environment = "prod"  # or dev, test
docker_image = "ghcr.io/your-org/ai-agent:latest"
azure_openai_api_key = "${var.azure_openai_api_key}"  # From GitHub Secret
azure_openai_endpoint = "${var.azure_openai_endpoint}"  # From GitHub Secret
azure_openai_deployment_name = "${var.azure_openai_deployment_name}"  # From GitHub Secret

# Container configuration
container_port = 8000
cpu_limit = "1.0"      # Increase for production
memory_limit = "2Gi"   # Increase for production
min_replicas = 2       # Increase for production
max_replicas = 10      # Increase for production

# =============================================================================
# SECURITY NOTES
# =============================================================================

# 1. NEVER commit sensitive values to version control
# 2. Use GitHub Secrets for all API keys and sensitive information
# 3. Environment variables are injected at runtime via GitHub Actions
# 4. Different secrets should be used for different environments
# 5. Rotate secrets regularly
# 6. Use Azure Key Vault as an additional security layer if needed

# =============================================================================
# DEPLOYMENT FLOW
# =============================================================================

# 1. Developer pushes code to main branch
# 2. GitHub Actions triggers build and deployment
# 3. Docker image is built and pushed to GitHub Container Registry
# 4. Terraform is executed with secrets from GitHub
# 5. Azure Container App is updated with new image
# 6. Environment variables are set from GitHub Secrets
# 7. Health checks verify successful deployment
