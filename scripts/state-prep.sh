#!/usr/bin/env bash
# state-prep.sh — Runs before every Terragrunt plan/apply/destroy in dev.
#
# WHY PER-BRANCH STATE:
#   Each branch gets its own state file so multiple branches can have their own
#   Container App simultaneously without overwriting each other's Terraform state.
#   Shared infrastructure (resource group, monitoring, cosmos, container app environment)
#   is imported into each branch's state on first use so Terraform doesn't try to create
#   resources that already exist. On destroy, only the branch's Container App is targeted.
#
# Expected env vars (injected by .deployer_aca.yml):
#   stack_prefix, app_env, branch_slug, repo_name
#   azure_subscription_id, vnet_resource_group_name, vnet_name
#
# NOTE: azurerm_subnet and NSG association removals are handled declaratively in
#       infra/migrations.tf via `removed` blocks.

set -euo pipefail

# ─── Derived resource names (must match infra/ naming conventions) ────────────
APP_NAME="${stack_prefix}-${app_env}"
RG_NAME="${repo_name}-${app_env}"
SUB="subscriptions/${azure_subscription_id}"

# Validate required environment variables before proceeding
echo "==> Validating required environment variables..."
REQUIRED_VARS=("stack_prefix" "app_env" "repo_name" "azure_subscription_id")
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var:-}" ]; then
    echo "✗ ERROR: Required environment variable '$var' is not set"
    echo "Expected vars: ${REQUIRED_VARS[*]}"
    exit 1
  fi
done
echo "✓ All required variables present"
echo "  stack_prefix: $stack_prefix"
echo "  app_env: $app_env"
echo "  repo_name: $repo_name"
echo "  azure_subscription_id: $azure_subscription_id"
echo ""

# ─── Resource IDs for all shared resources ────────────────────────────────────
RG_ID="/${SUB}/resourceGroups/${RG_NAME}"
LAW_ID="${RG_ID}/providers/Microsoft.OperationalInsights/workspaces/${APP_NAME}-log-analytics-workspace"
AI_ID="${RG_ID}/providers/Microsoft.Insights/components/${APP_NAME}-appinsights"
COSMOS_ACCT_ID="${RG_ID}/providers/Microsoft.DocumentDB/databaseAccounts/${APP_NAME}-cosmosdb-sql"
COSMOS_DB_ID="${COSMOS_ACCT_ID}/sqlDatabases/cosmosDatabase"
COSMOS_CONTAINER_ID="${COSMOS_DB_ID}/containers/cosmosContainer"
CA_ENV_NAME="${APP_NAME}-${app_env}-containerenv"
CA_ENV_ID="${RG_ID}/providers/Microsoft.App/managedEnvironments/${CA_ENV_NAME}"

# Print derived names for debugging
echo "==> Resource name mapping:"
echo "  APP_NAME (stack_prefix-app_env):  ${APP_NAME}   ← used for app resources (monitoring, cosmos, ACA)"
echo "  RG_NAME  (repo_name-app_env):     ${RG_NAME}    ← used for NSG names, resource group"
echo "  vnet_resource_group_name:         ${vnet_resource_group_name:-not set} ← networking RG (NSGs, subnets)"
echo "  vnet_name:                        ${vnet_name:-not set}"
echo ""

# ─── Init + single remote state fetch ────────────────────────────────────────
echo "==> Initializing Terragrunt..."
if ! terragrunt init -upgrade 2>&1; then
  echo "✗ FAILED: Terragrunt init failed"
  echo "  This usually means:"
  echo "    - Backend storage account doesn't exist"
  echo "    - Azure authentication failed"
  echo "    - Credentials don't have sufficient permissions"
  exit 1
fi
echo "✓ Terragrunt initialization successful"
echo ""

echo "==> Validating backend connection..."
if ! terragrunt validate-backend 2>&1; then
  echo "⚠ WARNING: Backend validation failed, but continuing (may be first deployment)..."
else
  echo "✓ Backend connection validated"
fi
echo ""

echo "==> Fetching state (single remote call)..."
if STATE=$(terragrunt state list 2>/dev/null); then
  echo "✓ Successfully fetched state list"
else
  STATE=""
  echo "⚠ WARNING: Could not fetch state list (may be empty)"
fi
echo ""

# Helper: import a resource if it's absent from state and exists in Azure.
# Usage: import_if_missing <state_address> <azure_resource_id>
import_if_missing() {
  local addr="$1"
  local id="$2"
  # Escape dots for grep so module addresses match literally
  local escaped
  escaped=$(echo "$addr" | sed 's/\./\\./g')
  
  # Check if resource is already in state
  if [ -z "$STATE" ] || ! echo "$STATE" | grep -q "${escaped}"; then
    echo "  Importing ${addr}..."
    if terragrunt import -lock=false "${addr}" "${id}" 2>/dev/null; then
      echo "  Successfully imported ${addr}"
    else
      echo "  Import of ${addr} skipped (resource may not exist yet or already in state)"
    fi
  else
    echo "  ${addr} already in state"
  fi
}

# ─── Remove stale resources (no longer in Terraform config) ──────────────────
# These can't use the helper because we're removing, not importing.

echo "==> Removing stale module.frontdoor resources..."
FRONTDOOR=$(echo "$STATE" | grep -E 'module\.frontdoor(\[|\.)' || true)
if [ -n "$FRONTDOOR" ]; then
  while IFS= read -r r; do
    terragrunt state rm -lock=false "$r" || true
  done <<< "$FRONTDOOR"
fi

echo "==> Removing stale module.api resources..."
API=$(echo "$STATE" | grep -E 'module\.api(\[|\.)' || true)
if [ -n "$API" ]; then
  while IFS= read -r r; do
    terragrunt state rm -lock=false "$r" || true
  done <<< "$API"
fi

# ─── Import shared infrastructure ────────────────────────────────────────────
# These resources already exist in Azure (created by the master/first-ever deploy).
# Each branch needs them in its own state so Terraform knows their current values
# and doesn't try to re-create them.

echo "==> Importing shared infrastructure into branch state..."

# 1. Resource group — root dependency of everything
# First check if the RG actually exists in Azure before importing
echo "  Checking if Resource Group exists in Azure: ${RG_NAME}..."
RG_EXISTS=$(az group exists --name "${RG_NAME}" 2>/dev/null || echo "false")
if [ "$RG_EXISTS" = "true" ]; then
  echo "  Resource Group exists in Azure, checking if it's in Terraform state..."
  
  # Check if already in state
  if echo "$STATE" | grep -q "azurerm_resource_group\.main"; then
    echo "  Resource Group already in Terraform state"
  else
    echo "  Resource Group NOT in state, importing now..."
    # Import with explicit error handling
    if terragrunt import -lock=false "azurerm_resource_group.main" "${RG_ID}" 2>&1; then
      echo "  ✓ Successfully imported Resource Group into state"
    else
      echo "  ✗ FAILED to import Resource Group. This resource must be in state before apply."
      echo "  Resource ID: ${RG_ID}"
      exit 1
    fi
  fi
else
  echo "  Resource Group does not exist in Azure yet, will be created by apply"
fi

# 2. Log Analytics workspace — required by container app environment
import_if_missing \
  "module.monitoring.azurerm_log_analytics_workspace.main" \
  "${LAW_ID}"

# 3. Application Insights — provides connection string + instrumentation key to containers
import_if_missing \
  "module.monitoring.azurerm_application_insights.main" \
  "${AI_ID}"

# 4. CosmosDB account — provides endpoint and account details
import_if_missing \
  "module.cosmos.azurerm_cosmosdb_account.cosmosdb_sql" \
  "${COSMOS_ACCT_ID}"

# 5. CosmosDB SQL database — provides database name
import_if_missing \
  "module.cosmos.azurerm_cosmosdb_sql_database.cosmosdb_sql_db" \
  "${COSMOS_DB_ID}"

# 6. CosmosDB SQL container — provides container name
import_if_missing \
  "module.cosmos.azurerm_cosmosdb_sql_container.cosmosdb_sql_db_container" \
  "${COSMOS_CONTAINER_ID}"

# 7. CosmosDB private endpoint
import_if_missing \
  "module.cosmos.azurerm_private_endpoint.cosmosdb_sql_db_private_endpoint" \
  "${RG_ID}/providers/Microsoft.Network/privateEndpoints/${APP_NAME}-cosmosdb-pe"

# 8. CosmosDB diagnostic setting
import_if_missing \
  "module.cosmos.azurerm_monitor_diagnostic_setting.cosmosdb_sql_diagnostics" \
  "${COSMOS_ACCT_ID}|${APP_NAME}-cosmosdb-diagnostics"

# 7. Container App Environment — shared across all branches (one per dev environment)
#    Use az CLI here since this resource requires the environment to actually exist
#    before we attempt import (unlike the others which have deterministic IDs).
if ! echo "$STATE" | grep -q 'module\.container_apps\.azurerm_container_app_environment\.main'; then
  echo "  Checking Azure for Container App Environment: ${CA_ENV_NAME}..."
  EXISTING_ENV=$(az containerapp env show \
    --name "${CA_ENV_NAME}" \
    --resource-group "${RG_NAME}" \
    --query id -o tsv 2>/dev/null || true)
  if [ -n "$EXISTING_ENV" ]; then
    echo "  Importing Container App Environment..."
    terragrunt import -lock=false \
      "module.container_apps.azurerm_container_app_environment.main" \
      "${EXISTING_ENV}" || true
  else
    echo "  Container App Environment not yet in Azure — will be created by apply"
  fi
else
  echo "  module.container_apps.azurerm_container_app_environment.main already in state"
fi

# 8. Backend Container App — the actual application running in the environment
#    Only import if it's NOT already in state and does exist in Azure
#    The backend ACA is named using the APP_NAME (stack prefix + environment)
if ! echo "$STATE" | grep -q 'module\.container_apps\.azurerm_container_app\.backend'; then
  echo "  Checking Azure for Backend Container App: ${APP_NAME}-api..."
  EXISTING_CA=$(az containerapp show \
    --name "${APP_NAME}-api" \
    --resource-group "${RG_NAME}" \
    --query id -o tsv 2>/dev/null || true)
  if [ -n "$EXISTING_CA" ]; then
    # Azure CLI returns ID with lowercase "containerapps", but Terraform expects camelCase "containerApps"
    # Fix the casing so Terraform can parse the ID correctly
    EXISTING_CA_FIXED=$(echo "$EXISTING_CA" | sed 's|/containerapps/|/containerApps/|g')
    
    echo "  Importing Backend Container App (${APP_NAME}-api)..."
    if terragrunt import -lock=false \
      "module.container_apps.azurerm_container_app.backend" \
      "${EXISTING_CA_FIXED}" 2>&1; then
      echo "  ✓ Successfully imported Backend Container App"
    else
      echo "  ✗ FAILED to import Backend Container App"
      echo "  Resource ID: ${EXISTING_CA_FIXED}"
      exit 1
    fi
  else
    echo "  Backend Container App not yet in Azure — will be created by apply"
  fi
else
  echo "  module.container_apps.azurerm_container_app.backend already in state"
fi

# ─── Non-dev: network resource imports ───────────────────────────────────────
# In test/prod the network module creates NSGs and subnets managed by Terraform.
# NSG names use RG_NAME (e.g. nr-ai-form-test), NOT APP_NAME (e.g. nraif-671b-test).
# NSGs and subnets live in vnet_resource_group_name (networking RG), not the app RG.
if [ "${app_env}" != "dev" ]; then
  echo "==> Checking network resource imports (non-dev)..."
  VNET_RG_ID="/${SUB}/resourceGroups/${vnet_resource_group_name}"
  VNET_ID="${VNET_RG_ID}/providers/Microsoft.Network/virtualNetworks/${vnet_name}"

  # NSG for Private Endpoints subnet — name uses RG_NAME, NOT APP_NAME
  import_if_missing \
    "module.network.azurerm_network_security_group.privateendpoints[0]" \
    "${VNET_RG_ID}/providers/Microsoft.Network/networkSecurityGroups/${RG_NAME}-pe-nsg"

  # NSG for Container Apps subnet — name uses RG_NAME, NOT APP_NAME
  import_if_missing \
    "module.network.azurerm_network_security_group.container_apps[0]" \
    "${VNET_RG_ID}/providers/Microsoft.Network/networkSecurityGroups/${RG_NAME}-ca-nsg"

  # Private Endpoints subnet
  import_if_missing \
    "module.network.azapi_resource.privateendpoints_subnet[0]" \
    "${VNET_ID}/subnets/privateendpoints-subnet"

  # Container Apps subnet
  import_if_missing \
    "module.network.azapi_resource.container_apps_subnet[0]" \
    "${VNET_ID}/subnets/container-apps-subnet"
fi

# ─── Front Door imports (test/prod only — dev has enable_front_door=false) ───
echo "==> Checking Front Door imports..."
STRIPPED=$(echo "$APP_NAME" | tr -cd 'a-zA-Z0-9')
import_if_missing \
  'module.frontdoor[0].azurerm_cdn_frontdoor_profile.frontend_frontdoor' \
  "${RG_ID}/providers/Microsoft.Cdn/profiles/${APP_NAME}-frontend-frontdoor"

import_if_missing \
  'module.frontdoor[0].azurerm_cdn_frontdoor_firewall_policy.frontend_firewall_policy' \
  "${RG_ID}/providers/Microsoft.Network/frontDoorWebApplicationFirewallPolicies/${STRIPPED}frontendfirewall"

# Front Door endpoint (api_fd_endpoint) — only if Front Door profile exists
import_if_missing \
  'module.container_apps.azurerm_cdn_frontdoor_endpoint.api_fd_endpoint[0]' \
  "${RG_ID}/providers/Microsoft.Cdn/profiles/${APP_NAME}-frontend-frontdoor/afdEndpoints/${repo_name}-${app_env}-api-fd"

# Front Door origin group (api_origin_group)
import_if_missing \
  'module.container_apps.azurerm_cdn_frontdoor_origin_group.api_origin_group[0]' \
  "${RG_ID}/providers/Microsoft.Cdn/profiles/${APP_NAME}-frontend-frontdoor/originGroups/${repo_name}-${app_env}-api-origin-group"

# Front Door security policy (WAF) — security policy attached to endpoint
import_if_missing \
  'module.container_apps.azurerm_cdn_frontdoor_security_policy.frontend_fd_security_policy[0]' \
  "${RG_ID}/providers/Microsoft.Cdn/profiles/${APP_NAME}-frontend-frontdoor/securityPolicies/${APP_NAME}-api-fd-waf-security-policy"

# Front Door origin (the origin entry inside the origin group)
import_if_missing \
  'module.container_apps.azurerm_cdn_frontdoor_origin.api_container_app_origin[0]' \
  "${RG_ID}/providers/Microsoft.Cdn/profiles/${APP_NAME}-frontend-frontdoor/originGroups/${repo_name}-${app_env}-api-origin-group/origins/${repo_name}-${app_env}-api-origin"

# Front Door route (api_route)
import_if_missing \
  'module.container_apps.azurerm_cdn_frontdoor_route.api_route[0]' \
  "${RG_ID}/providers/Microsoft.Cdn/profiles/${APP_NAME}-frontend-frontdoor/afdEndpoints/${repo_name}-${app_env}-api-fd/routes/${repo_name}-${app_env}-api-fd"

# ─── Diagnostic setting imports ───────────────────────────────────────────────
echo "==> Checking diagnostic setting imports..."
import_if_missing \
  'module.container_apps.azurerm_monitor_diagnostic_setting.container_app_env_diagnostics' \
  "${CA_ENV_ID}|${APP_NAME}-ca-env-diagnostics"

# Backend Container App diagnostics — ID contains the branch-specific Container App ID
if ! echo "$STATE" | grep -q 'module\.container_apps\.azurerm_monitor_diagnostic_setting\.backend_container_app_diagnostics'; then
  CA_BACKEND_ID=$(terragrunt state show 'module.container_apps.azurerm_container_app.backend' 2>/dev/null \
    | grep -E '^\s+id\s+=' | awk -F'"' '{print $2}' || true)
  if [ -n "$CA_BACKEND_ID" ]; then
    echo "  Importing backend_container_app_diagnostics..."
    terragrunt import -lock=false \
      'module.container_apps.azurerm_monitor_diagnostic_setting.backend_container_app_diagnostics' \
      "${CA_BACKEND_ID}|${APP_NAME}-backend-ca-diagnostics" \
      2>/dev/null || true
  fi
fi

# ─── Final verification ───────────────────────────────────────────────────────
echo "==> Verifying critical resources are in state..."

# Refresh state to get latest
STATE=$(terragrunt state list 2>/dev/null || echo "")

# Check resource group
if echo "$STATE" | grep -q "azurerm_resource_group\.main"; then
  echo "✓ Resource Group is in state"
else
  echo "✗ ERROR: Resource Group NOT in state after import attempt"
  echo "  This means Terraform will try to CREATE the resource group, but it already exists in Azure"
  echo "  Manual recovery needed: terragrunt import azurerm_resource_group.main ${RG_ID}"
  exit 1
fi

echo "==> State prep complete - all critical resources verified in state"