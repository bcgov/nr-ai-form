# GitHub Actions OIDC Setup Scripts

This directory contains scripts to configure Azure resources for GitHub Actions OIDC authentication, including support for Terraform state storage.

## Scripts

### `setup-github-actions-oidc.sh`

The main script that creates and configures:
- User-assigned managed identity
- Federated identity credentials for GitHub Actions OIDC
- Role assignments for Azure resource access
- Optional: Storage account for Terraform state with proper security configuration

### `setup-examples.sh`

Example commands tailored to the nr-ai-form repository configuration.

## Prerequisites

1. **Azure CLI**: Install and login to Azure CLI
   ```bash
   az login
   ```

2. **Permissions**: You need sufficient permissions to:
   - Create managed identities
   - Assign roles
   - Create storage accounts (if using Terraform state)

## Usage

### Basic Setup

```bash
./scripts/setup-github-actions-oidc.sh \
  --resource-group "a9cee3-test-networking" \
  --identity-name "nr-ai-form-github-actions" \
  --github-repo "adamjwebb/nr-ai-form" \
  --branch "app_service_cosmos_db"
```

### With Terraform State Storage

```bash
./scripts/setup-github-actions-oidc.sh \
  --resource-group "a9cee3-test-networking" \
  --identity-name "nr-ai-form-github-actions" \
  --github-repo "adamjwebb/nr-ai-form" \
  --branch "app_service_cosmos_db" \
  --create-storage \
  --storage-account "nraiformtfstate" \
  --additional-roles "Key Vault Secrets User,Cosmos DB Account Reader Role"
```

### Environment-Specific Setup

```bash
./scripts/setup-github-actions-oidc.sh \
  --resource-group "a9cee3-test-networking" \
  --identity-name "nr-ai-form-github-actions-prod" \
  --github-repo "adamjwebb/nr-ai-form" \
  --environment "production" \
  --create-storage \
  --storage-account "nraiformtfstateprod"
```

## Options

| Option | Description | Required |
|--------|-------------|----------|
| `-g, --resource-group` | Azure resource group name | Yes |
| `-n, --identity-name` | Managed identity name | Yes |
| `-r, --github-repo` | GitHub repository (owner/repo) | Yes |
| `-e, --environment` | GitHub environment name | No |
| `-b, --branch` | GitHub branch name (default: main) | No |
| `-s, --subscription` | Azure subscription ID | No |
| `--contributor-scope` | Scope for Contributor role | No |
| `--additional-roles` | Additional roles (comma-separated) | No |
| `--storage-account` | Storage account name for Terraform | No |
| `--storage-container` | Storage container name (default: tfstate) | No |
| `--create-storage` | Create storage account for Terraform | No |
| `--dry-run` | Show what would be done | No |

## What the Script Creates

### Managed Identity
- User-assigned managed identity with the specified name
- Assigned to the specified resource group
- Configured with federated identity credentials for GitHub Actions

### Role Assignments
- **Contributor** role on the specified scope (default: resource group)
- **Storage Blob Data Contributor** role (if creating storage account)
- **Storage Account Contributor** role (if creating storage account)
- Any additional roles specified via `--additional-roles`

### Storage Account (Optional)
- Standard_LRS storage account with secure configuration:
  - TLS 1.2 minimum
  - HTTPS only
  - Public blob access disabled
  - Local user accounts disabled
  - Blob versioning enabled
- Storage container for Terraform state files

### Federated Identity Credentials
- Configured for GitHub Actions OIDC
- Subject claim based on repository and branch/environment
- Issuer: `https://token.actions.githubusercontent.com`
- Audience: `api://AzureADTokenExchange`

## GitHub Actions Integration

After running the script, add these secrets to your GitHub repository:

### Repository Secrets
- `AZURE_CLIENT_ID`: Client ID of the managed identity
- `AZURE_SUBSCRIPTION_ID`: Azure subscription ID
- `AZURE_TENANT_ID`: Azure tenant ID

### Environment Variables for Terraform
- `ARM_USE_AZUREAD`: true
- `ARM_SUBSCRIPTION_ID`: Azure subscription ID
- `ARM_TENANT_ID`: Azure tenant ID
- `ARM_CLIENT_ID`: Client ID of the managed identity

## Example GitHub Actions Workflow

```yaml
name: Deploy to Azure

on:
  push:
    branches: [ app_service_cosmos_db ]

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Azure Login
        uses: azure/login@v1
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: 1.5.0
      
      - name: Terraform Init
        run: terraform init
        working-directory: ./infra
        env:
          ARM_USE_AZUREAD: true
          ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
          ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
          ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
      
      - name: Terraform Plan
        run: terraform plan
        working-directory: ./infra
        env:
          ARM_USE_AZUREAD: true
          ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
          ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
          ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
      
      - name: Terraform Apply
        run: terraform apply -auto-approve
        working-directory: ./infra
        env:
          ARM_USE_AZUREAD: true
          ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
          ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
          ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
```

## Terraform Backend Configuration

If you used the `--create-storage` option, add this to your Terraform configuration:

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "a9cee3-test-networking"
    storage_account_name = "nraiformtfstate"
    container_name       = "tfstate"
    key                  = "terraform.tfstate"
    use_azuread_auth     = true
  }
}
```

## Security Considerations

- **No Storage Keys**: The setup uses Azure AD authentication instead of storage account keys
- **Least Privilege**: Only necessary roles are assigned
- **Secure Storage**: Storage account is configured with security best practices
- **OIDC**: Uses OpenID Connect for secure, keyless authentication
- **Scope Limitation**: Roles are scoped to the minimum required resources

## Troubleshooting

1. **Permission Errors**: Ensure you have sufficient permissions in Azure
2. **Storage Account Name**: Must be globally unique and 3-24 characters (lowercase letters and numbers only)
3. **GitHub Repository**: Must be in the format `owner/repo`
4. **Subscription**: Ensure you're using the correct Azure subscription

## Cleanup

To remove the resources created by this script:

```bash
# Remove the managed identity
az identity delete --name "nr-ai-form-github-actions" --resource-group "a9cee3-test-networking"

# Remove the storage account (if created)
az storage account delete --name "nraiformtfstate" --resource-group "a9cee3-test-networking"
```
