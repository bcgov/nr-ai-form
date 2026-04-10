#!/usr/bin/env bash
# state-prep.sh — Run before every Terragrunt plan/apply/destroy.
#
# Expects these env vars (set by .deployer_aca.yml):
#   stack_prefix, app_env, branch_slug, repo_name
#   azure_subscription_id, vnet_resource_group_name, vnet_name
#
# What this script does:
#   1. terragrunt init
#   2. Fetch state once — all subsequent checks are local string operations
#   3. Remove stale module.frontdoor and module.api resources (prevent unintended destroy)
#   4. Import resources that exist in Azure but are missing from this branch's state
#
# NOTE: azurerm_subnet and NSG association removals are handled declaratively in
#       infra/migrations.tf via `removed` blocks — no shell needed for those.

set -euo pipefail

echo "==> Initializing Terragrunt..."
terragrunt init -upgrade

echo "==> Fetching state (single call)..."
STATE=$(terragrunt state list 2>/dev/null || true)

# Derived names used in Azure resource IDs
APP_NAME="${stack_prefix}-${app_env}"
RG_NAME="${repo_name}-${app_env}"
CA_ENV_NAME="${APP_NAME}-${app_env}-containerenv"
CA_ENV_ID="/subscriptions/${azure_subscription_id}/resourceGroups/${RG_NAME}/providers/Microsoft.App/managedEnvironments/${CA_ENV_NAME}"

# ─── Import root shared resources (first-deploy / fresh state guard) ────────
# The resource group is a root dependency of every module. If it already exists
# in Azure but not in state, every apply would fail trying to create it.

echo "==> Checking resource group import..."
if ! echo "$STATE" | grep -q 'azurerm_resource_group\.main'; then
  echo "  Resource group not in state, checking Azure..."
  EXISTING_RG=$(az group show --name "${RG_NAME}" --query id -o tsv 2>/dev/null || true)
  if [ -n "$EXISTING_RG" ]; then
    echo "  Importing resource group: ${RG_NAME}"
    terragrunt import -lock=false 'azurerm_resource_group.main' "$EXISTING_RG" || true
    STATE=$(terragrunt state list 2>/dev/null || true)
  fi
fi

# ─── Remove stale resources (prevent_destroy guard won't catch these because ───
# ─── they no longer exist in the Terraform config)                            ───

echo "==> Checking for stale module.frontdoor resources..."
FRONTDOOR_RESOURCES=$(echo "$STATE" | grep -E 'module\.frontdoor(\[|\.)' || true)
if [ -n "$FRONTDOOR_RESOURCES" ]; then
  echo "  Removing stale module.frontdoor resources from state..."
  while IFS= read -r resource; do
    terragrunt state rm -lock=false "$resource" || true
  done <<< "$FRONTDOOR_RESOURCES"
else
  echo "  No stale module.frontdoor resources"
fi

echo "==> Checking for stale module.api resources..."
API_RESOURCES=$(echo "$STATE" | grep -E 'module\.api(\[|\.)' || true)
if [ -n "$API_RESOURCES" ]; then
  echo "  Removing stale module.api resources from state..."
  while IFS= read -r resource; do
    terragrunt state rm -lock=false "$resource" || true
  done <<< "$API_RESOURCES"
else
  echo "  No stale module.api resources"
fi

# ─── Imports — bring existing Azure resources into this branch's state ───────

# Container Apps subnet — only managed by Terraform in non-dev environments
# (dev uses a pre-existing subnet via hardcoded ID in terragrunt/dev/terragrunt.hcl)
if [ "${app_env}" != "dev" ]; then
  echo "==> Checking container-apps-subnet import (non-dev)..."
  SUBNET_ID="/subscriptions/${azure_subscription_id}/resourceGroups/${vnet_resource_group_name}/providers/Microsoft.Network/virtualNetworks/${vnet_name}/subnets/container-apps-subnet"
  if ! echo "$STATE" | grep -q 'module\.network\.azapi_resource\.container_apps_subnet'; then
    echo "  Importing container-apps-subnet..."
    terragrunt import -lock=false "module.network.azapi_resource.container_apps_subnet[0]" "$SUBNET_ID" 2>/dev/null || true
  else
    echo "  container-apps-subnet already in state"
  fi
fi

# Front Door profile — only present when enable_front_door=true (test/prod)
echo "==> Checking Front Door imports..."
STRIPPED=$(echo "$APP_NAME" | tr -cd 'a-zA-Z0-9')
if ! echo "$STATE" | grep -q 'module\.frontdoor\[0\]\.azurerm_cdn_frontdoor_profile\.frontend_frontdoor'; then
  terragrunt import -lock=false \
    'module.frontdoor[0].azurerm_cdn_frontdoor_profile.frontend_frontdoor' \
    "/subscriptions/${azure_subscription_id}/resourceGroups/${RG_NAME}/providers/Microsoft.Cdn/profiles/${APP_NAME}-frontend-frontdoor" \
    2>/dev/null || true
fi

if ! echo "$STATE" | grep -q 'module\.frontdoor\[0\]\.azurerm_cdn_frontdoor_firewall_policy\.frontend_firewall_policy'; then
  terragrunt import -lock=false \
    'module.frontdoor[0].azurerm_cdn_frontdoor_firewall_policy.frontend_firewall_policy' \
    "/subscriptions/${azure_subscription_id}/resourceGroups/${RG_NAME}/providers/Microsoft.Network/frontDoorWebApplicationFirewallPolicies/${STRIPPED}frontendfirewall" \
    2>/dev/null || true
fi

# Diagnostic settings — environment diagnostics
echo "==> Checking diagnostic setting imports..."
if ! echo "$STATE" | grep -q 'module\.container_apps\.azurerm_monitor_diagnostic_setting\.container_app_env_diagnostics'; then
  terragrunt import -lock=false \
    'module.container_apps.azurerm_monitor_diagnostic_setting.container_app_env_diagnostics' \
    "${CA_ENV_ID}|${APP_NAME}-ca-env-diagnostics" \
    2>/dev/null || true
fi

# Diagnostic settings — backend Container App diagnostics
# Fetch the Container App ID from state dynamically (name includes branch_slug so it varies)
if ! echo "$STATE" | grep -q 'module\.container_apps\.azurerm_monitor_diagnostic_setting\.backend_container_app_diagnostics'; then
  CA_BACKEND_ID=$(terragrunt state show 'module.container_apps.azurerm_container_app.backend' 2>/dev/null \
    | grep -E '^\s+id\s+=' | awk -F'"' '{print $2}' || true)
  if [ -n "$CA_BACKEND_ID" ]; then
    terragrunt import -lock=false \
      'module.container_apps.azurerm_monitor_diagnostic_setting.backend_container_app_diagnostics' \
      "${CA_BACKEND_ID}|${APP_NAME}-backend-ca-diagnostics" \
      2>/dev/null || true
  fi
fi

echo "==> State prep complete"
