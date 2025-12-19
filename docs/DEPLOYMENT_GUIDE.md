# Deployment Guide: App Service vs Azure Container Apps# Deployment Guide



This project supports **two deployment types** using conditional Terraform logic in a single `main.tf` file.This guide provides step-by-step instructions for deploying the infrastructure and API for this project using GitHub Actions, Terraform, and supporting scripts.



## 📋 Overview---



The infrastructure uses a `deployment_type` variable to conditionally deploy **either** App Service **or** Azure Container Apps (ACA) - never both simultaneously.## Prerequisites



## 🚀 Deployment Options- Azure CLI installed, authenticated and context set to desired Azure Subscription

- Sufficient permissions to create resources in your Azure subscription

### Option 1: App Service (Default)- GitHub repository admin access



**Workflows:** `deploy-to-dev.yml`, `deploy-to-tes.yml`  ---

**Deploys:** `azurerm_linux_web_app` (App Service)

## 1. Set Up GitHub OIDC and Terraform State Storage

### Option 2: Azure Container Apps

A setup script is provided to automate the creation of:

**Workflows:** `deploy-aca-dev.yml`, `deploy-aca-test.yml`  - Azure resources for GitHub OpenID Connect (OIDC) authentication

**Deploys:** `azurerm_container_app` (Azure Container Apps)- A storage account for Terraform state



## 🔧 How It Works**Run the setup script:**



The `main.tf` file uses conditional logic:```bash

bash scripts/setup-github-actions-oidc.sh

```terraform```

# App Service (when deployment_type = "app_service")

module "api" {This script will:

  count = var.deployment_type == "app_service" ? 1 : 0- Create an Azure User-Assigned Managed Identity and federated credentials for GitHub Actions OIDC

  ...- Create a storage account for Terraform state

}- Output values needed for GitHub secrets and environment variables



# Container Apps (when deployment_type = "container_apps")---

module "container_apps" {## 2. Add Managed Identity to Project Entra Contributor Group

  count = var.deployment_type == "container_apps" ? 1 : 0

  ...After running the setup script, a project lead must manually add the newly created Azure User-Assigned Managed Identity to the Entra group that assigns the Contributor role for this project. This step is required to ensure the GitHub Actions workflow has sufficient permissions to deploy resources.

}

```**Manual action required:**

- Identify the managed identity name from the setup script output

Only ONE module is created based on the `deployment_type` variable.- In the Entra admin portal, add this managed identity to the appropriate group that grants Contributor access

- Confirm the group assignment is complete before proceeding

## 📊 Comparison

---

| Feature | App Service | Container Apps |## 3. Create GitHub Environment

|---------|-------------|----------------|

| **Resource** | `azurerm_linux_web_app` | `azurerm_container_app` |In your GitHub repository:

| **Pricing** | Fixed monthly | Consumption-based |1. Go to **Settings > Environments**

| **Scaling** | Manual/auto-scale | HTTP auto-scaling (0-10) |2. Click **New environment** and name it (e.g., `development` or `production`)

| **Cost** | Fixed cost | Pay per use |3. Save the environment

| **Workflows** | `deploy-to-*.yml` | `deploy-aca-*.yml` |

---

## 🎯 Usage

## 4. Add GitHub Secrets and Variables

### Deploy App Service to Dev

1. Go to **GitHub Actions**Add the following secrets and variables to your environment (as output by the setup script):

2. Run **"Deploy to Dev"**

### Required Secrets

### Deploy Container Apps to Dev- `AZURE_CLIENT_ID` – From setup script output

1. Go to **GitHub Actions**- `AZURE_TENANT_ID` – From setup script output

2. Run **"Deploy ACA to Dev"**- `AZURE_SUBSCRIPTION_ID` – Your Azure subscription ID



## 🎉 Summary### Required Variables

- `APIM_SUBNET_PREFIX` – CIDR for APIM subnet (e.g., `10.46.8.0/26`)

- **ONE** `main.tf` file supports BOTH deployment types- `APP_SERVICE_SUBNET_PREFIX` – CIDR for App Service subnet (e.g., `10.46.8.64/26`)

- **App Service (Default):** Use `deploy-to-dev` / `deploy-to-tes` workflows- `PRIVATEENDPOINT_SUBNET_PREFIX` – CIDR for Private Endpoint subnet (e.g., `10.46.8.128/26`)

- **Container Apps (New):** Use `deploy-aca-dev` / `deploy-aca-test` workflows- `RESOURCE_GROUP_NAME` – Name of the Azure Resource Group to host the Azure Resources (e.g., `a9cee3-test-networking`)

- **Variable controlled:** `deployment_type` determines which resources are created- `TFSTATE_STORAGE_ACCOUNT` – Name of the storage account for Terraform state

- `VNET_NAME` – Name of the Azure vNet
---

## 5. Deploy Infrastructure with GitHub Actions

Once secrets and variables are set, push changes to your repository. The GitHub Actions workflow will:
- Authenticate to Azure using OIDC
- Initialize and apply Terraform to provision infrastructure
- Deploy the API to Azure App Service

Monitor workflow runs under the **Actions** tab in your repository.

---

## 6. Troubleshooting

- Ensure all secrets and variables are correctly set
- Check workflow logs for errors
- Verify Azure resources are created as expected

---

For more details, see the `scripts/README.md` and `docs/GITHUB_ACTIONS_SETUP.md` files.
