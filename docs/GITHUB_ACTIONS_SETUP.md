# GitHub Actions Secrets and Variables Setup

## Overview
This document outlines the required secrets and variables for the GitHub Actions workflow to properly deploy your Terraform infrastructure.

## Required GitHub Secrets

### Azure Authentication (Repository Secrets)
Set these in your repository: `Settings > Secrets and variables > Actions > Repository secrets`

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `AZURE_CLIENT_ID` | Azure AD Application (Service Principal) Client ID | `12345678-1234-1234-1234-123456789012` |
| `AZURE_SUBSCRIPTION_ID` | Azure Subscription ID where resources will be deployed | `9b6ae7b5-90fb-4b00-96b3-5a10cc0cb0a3` |
| `AZURE_TENANT_ID` | Azure AD Tenant ID | `87654321-4321-4321-4321-210987654321` |

### Container Registry (Repository Secrets)
| Secret Name | Description |
|------------|-------------|
| `CONTAINER_REGISTRY_USERNAME` | Container registry username |
| `CONTAINER_REGISTRY_PASSWORD` | Container registry password |

## Required GitHub Variables

### Environment Variables (Repository or Environment Variables)
Set these in: `Settings > Secrets and variables > Actions > Variables`

| Variable Name | Description | Example Value |
|--------------|-------------|---------------|
| `RESOURCE_GROUP` | Resource group containing Terraform state storage | `rg-terraform-state` |
| `TF_STATE_STORAGE_ACCOUNT` | Storage account for Terraform state | `tfstatestorage12345` |

### Container Configuration
| Variable Name | Description | Example Value |
|--------------|-------------|---------------|
| `CONTAINER_IMAGE_NAME` | Container image name | `myapp:latest` |
| `CONTAINER_REGISTRY_URL` | Container registry URL | `https://myregistry.azurecr.io` |

## Environment-Specific Configuration

### Development Environment
- Uses secrets and variables from the `development` environment
- Deploys to development subscription

### Production Environment
- Uses secrets and variables from the `production` environment
- Deploys to production subscription
- Only deploys on push to `main` branch

## Setup Instructions

### 1. Create Azure Service Principal with OIDC
```bash
# Create service principal
az ad sp create-for-rbac --name "github-actions-sp" --role contributor --scopes /subscriptions/YOUR_SUBSCRIPTION_ID

# Configure OIDC
az ad app federated-credential create \
  --id YOUR_CLIENT_ID \
  --parameters '{
    "name": "github-actions-oidc",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:YOUR_GITHUB_USERNAME/YOUR_REPO_NAME:ref:refs/heads/main",
    "description": "GitHub Actions OIDC for main branch",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### 2. Set GitHub Repository Secrets
```bash
# Using GitHub CLI
gh secret set AZURE_CLIENT_ID --body "your-client-id"
gh secret set AZURE_SUBSCRIPTION_ID --body "your-subscription-id"
gh secret set AZURE_TENANT_ID --body "your-tenant-id"
gh secret set CONTAINER_REGISTRY_USERNAME --body "your-username"
gh secret set CONTAINER_REGISTRY_PASSWORD --body "your-password"
```

### 3. Set GitHub Repository Variables
```bash
# Using GitHub CLI
gh variable set RESOURCE_GROUP --body "your-resource-group"
gh variable set TF_STATE_STORAGE_ACCOUNT --body "your-storage-account"
gh variable set CONTAINER_IMAGE_NAME --body "your-image:tag"
gh variable set CONTAINER_REGISTRY_URL --body "https://your-registry.azurecr.io"
```

## How It Works

1. **Azure Authentication**: The workflow uses OIDC to authenticate with Azure using the service principal
2. **Environment Variables**: ARM_* environment variables are automatically set for Terraform
3. **Subscription ID**: Terraform reads the subscription ID from the `ARM_SUBSCRIPTION_ID` environment variable
4. **State Management**: Terraform state is stored in Azure Storage with environment-specific keys
5. **Security**: No hardcoded credentials in code - everything is stored as GitHub secrets

## Troubleshooting

### Common Issues

1. **Missing Subscription ID**: Ensure `AZURE_SUBSCRIPTION_ID` secret is set
2. **OIDC Authentication Fails**: Verify federated credential is configured correctly
3. **Permission Denied**: Ensure service principal has proper permissions on the subscription
4. **State Access Issues**: Verify service principal has access to the Terraform state storage account

### Validation Commands

```bash
# Check if secrets are accessible in workflow
echo "Subscription ID: $ARM_SUBSCRIPTION_ID"
echo "Client ID: $ARM_CLIENT_ID"
echo "Tenant ID: $ARM_TENANT_ID"

# Test Azure authentication
az account show --query id
```

## Best Practices

1. **Use Environment-Specific Secrets**: Different subscriptions for dev/prod
2. **Least Privilege**: Service principal should have minimal required permissions
3. **Rotate Credentials**: Regularly rotate service principal credentials
4. **Monitor Access**: Enable logging for service principal usage
5. **Branch Protection**: Require PR reviews for production deployments
