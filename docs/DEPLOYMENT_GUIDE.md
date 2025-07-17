# Deployment Guide

This guide provides step-by-step instructions for deploying the infrastructure and API for this project using GitHub Actions, Terraform, and supporting scripts.

---

## Prerequisites

- Azure CLI installed, authenticated and context set to desired Azure Subscription
- Sufficient permissions to create resources in your Azure subscription
- GitHub repository admin access

---

## 1. Set Up GitHub OIDC and Terraform State Storage

A setup script is provided to automate the creation of:
- Azure resources for GitHub OpenID Connect (OIDC) authentication
- A storage account for Terraform state

**Run the setup script:**

```bash
bash scripts/setup-github-actions-oidc.sh
```

This script will:
- Create an Azure User-Assigned Managed Identity and federated credentials for GitHub Actions OIDC
- Create a storage account for Terraform state
- Output values needed for GitHub secrets and environment variables

---

## 2. Create GitHub Environment

In your GitHub repository:
1. Go to **Settings > Environments**
2. Click **New environment** and name it (e.g., `development` or `production`)
3. Save the environment

---

## 3. Add GitHub Secrets and Variables

Add the following secrets and variables to your environment (as output by the setup script):

### Required Secrets
- `AZURE_CLIENT_ID` – From setup script output
- `AZURE_TENANT_ID` – From setup script output
- `AZURE_SUBSCRIPTION_ID` – Your Azure subscription ID

### Required Variables
- `APIM_SUBNET_PREFIX` – CIDR for APIM subnet (e.g., `10.46.8.0/26`)
- `APP_SERVICE_SUBNET_PREFIX` – CIDR for App Service subnet (e.g., `10.46.8.64/26`)
- `PRIVATEENDPOINT_SUBNET_PREFIX` – CIDR for Private Endpoint subnet (e.g., `10.46.8.128/26`)
- `RESOURCE_GROUP_NAME` – Name of the Azure Resource Group to host the Azure Resources (e.g., `a9cee3-test-networking`)
- `TF_STATE_STORAGE_ACCOUNT` – Name of the storage account for Terraform state
- `VNET_NAME` – Name of the Azure vNet
---

## 4. Deploy Infrastructure with GitHub Actions

Once secrets and variables are set, push changes to your repository. The GitHub Actions workflow will:
- Authenticate to Azure using OIDC
- Initialize and apply Terraform to provision infrastructure
- Deploy the API to Azure App Service

Monitor workflow runs under the **Actions** tab in your repository.

---

## 5. Troubleshooting

- Ensure all secrets and variables are correctly set
- Check workflow logs for errors
- Verify Azure resources are created as expected

---

For more details, see the `scripts/README.md` and `docs/GITHUB_ACTIONS_SETUP.md` files.
