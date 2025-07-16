#!/bin/bash

# Example script to setup GitHub Actions OIDC for the nr-ai-form repository
# This script demonstrates how to use the main setup script with your current project

# Configuration based on your current repository
RESOURCE_GROUP="a9cee3-test-networking"  # From your variables.tf
IDENTITY_NAME="nr-ai-form-github-actions"
GITHUB_REPO="adamjwebb/nr-ai-form"
GITHUB_BRANCH="app_service_cosmos_db"  # Your current branch

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up GitHub Actions OIDC for nr-ai-form repository${NC}"
echo ""

# Basic setup without storage account
echo -e "${GREEN}Option 1: Basic setup (no Terraform storage)${NC}"
echo "./scripts/setup-github-actions-oidc.sh \\"
echo "  --resource-group '$RESOURCE_GROUP' \\"
echo "  --identity-name '$IDENTITY_NAME' \\"
echo "  --github-repo '$GITHUB_REPO' \\"
echo "  --branch '$GITHUB_BRANCH'"
echo ""

# Setup with Terraform storage account
echo -e "${GREEN}Option 2: Setup with Terraform state storage (auto-generated name)${NC}"
echo "./scripts/setup-github-actions-oidc.sh \\"
echo "  --resource-group '$RESOURCE_GROUP' \\"
echo "  --identity-name '$IDENTITY_NAME' \\"
echo "  --github-repo '$GITHUB_REPO' \\"
echo "  --branch '$GITHUB_BRANCH' \\"
echo "  --create-storage \\"
echo "  --additional-roles 'Key Vault Secrets User,Cosmos DB Account Reader Role'"
echo ""

# Setup with custom storage account name
echo -e "${GREEN}Option 3: Setup with custom storage account name${NC}"
echo "./scripts/setup-github-actions-oidc.sh \\"
echo "  --resource-group '$RESOURCE_GROUP' \\"
echo "  --identity-name '$IDENTITY_NAME' \\"
echo "  --github-repo '$GITHUB_REPO' \\"
echo "  --branch '$GITHUB_BRANCH' \\"
echo "  --create-storage \\"
echo "  --storage-account 'mycustomstorageaccount' \\"
echo "  --additional-roles 'Key Vault Secrets User,Cosmos DB Account Reader Role'"
echo ""

# Setup for production environment
echo -e "${GREEN}Option 4: Setup for production environment${NC}"
echo "./scripts/setup-github-actions-oidc.sh \\"
echo "  --resource-group '$RESOURCE_GROUP' \\"
echo "  --identity-name '$IDENTITY_NAME-prod' \\"
echo "  --github-repo '$GITHUB_REPO' \\"
echo "  --environment 'production' \\"
echo "  --create-storage \\"
echo "  --storage-account 'nraiformtfstateprod' \\"
echo "  --additional-roles 'Key Vault Secrets User,Cosmos DB Account Reader Role'"
echo ""

# Dry run example
echo -e "${GREEN}Option 5: Dry run to see what would be done${NC}"
echo "./scripts/setup-github-actions-oidc.sh \\"
echo "  --resource-group '$RESOURCE_GROUP' \\"
echo "  --identity-name '$IDENTITY_NAME' \\"
echo "  --github-repo '$GITHUB_REPO' \\"
echo "  --branch '$GITHUB_BRANCH' \\"
echo "  --create-storage \\"
echo "  --dry-run"
echo ""

echo -e "${BLUE}Choose an option and run the corresponding command${NC}"
echo "Make sure you're logged in to Azure CLI first: az login"
