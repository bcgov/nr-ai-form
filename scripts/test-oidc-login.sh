#!/bin/bash
# Test Azure OIDC login from GitHub Actions
# This script simulates the azure/login@v2 action behavior

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Testing Azure OIDC Login Configuration${NC}"
echo "=========================================="

# Check if running in GitHub Actions
if [ -z "$GITHUB_ACTIONS" ]; then
    echo -e "${RED}ERROR: This script must be run inside a GitHub Actions workflow${NC}"
    echo ""
    echo "Create a test workflow like this:"
    echo ""
    cat << 'EOF'
name: Test OIDC Login
on:
  workflow_dispatch:
    inputs:
      environment_name:
        description: 'Environment to test (dev/test)'
        required: true
        default: 'dev'
        type: choice
        options:
          - dev
          - test

permissions:
  id-token: write
  contents: read

jobs:
  test-login:
    name: Test Azure OIDC Login
    runs-on: ubuntu-24.04
    environment: ${{ inputs.environment_name }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Test Azure Login
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      
      - name: Verify Login
        run: |
          echo "✅ Login successful!"
          az account show
          az ad signed-in-user show 2>/dev/null || echo "Service Principal login (expected)"
EOF
    exit 1
fi

echo ""
echo "Environment: ${GITHUB_ENVIRONMENT:-not set}"
echo "Repository: ${GITHUB_REPOSITORY}"
echo "Ref: ${GITHUB_REF}"
echo "SHA: ${GITHUB_SHA}"
echo ""

# The azure/login action will handle the OIDC flow
# This script is just for verification after login

echo -e "${GREEN}Checking Azure CLI login status...${NC}"
if az account show &>/dev/null; then
    echo -e "${GREEN}✅ Azure CLI is logged in${NC}"
    echo ""
    az account show --output table
    echo ""
    
    # Try to get the service principal details
    echo -e "${GREEN}Service Principal Details:${NC}"
    az account show --query "{TenantId:tenantId, SubscriptionId:id, SubscriptionName:name}" -o table
    
    echo ""
    echo -e "${GREEN}✅ OIDC login test PASSED${NC}"
    exit 0
else
    echo -e "${RED}❌ Azure CLI is not logged in${NC}"
    exit 1
fi
