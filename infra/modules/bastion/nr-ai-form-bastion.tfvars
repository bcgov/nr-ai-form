# =============================================================================
# nr-ai-form Bastion + Jumpbox configuration
#
# Used by: .github/workflows/deploy-bastion.yml
# Consumed by: bcgov/action-deployer-vm-bastion-alz@v1
#
# DO NOT put secrets here. subscription_id, client_id, tenant_id and
# all VNet/subnet details are supplied via GitHub Environment secrets in
# the workflow. This file holds only non-sensitive tuning values.
# =============================================================================

# --- Identity / namespace --------------------------------------------------
app_name = "nr-ai-form"
# app_env is injected by the workflow via the app_env input, not set here.

# Azure region. Canada Central is the default; override if needed.
# location = "Canada Central"

# Resource group name defaults to "<app_name>-<app_env>" when not set.
# resource_group_name = "nr-ai-form-dev"

# --- Network / subnets -----------------------------------------------------
# Subnet CIDRs are required but kept in GitHub secrets (BASTION_SUBNET_ADDRESS_PREFIX
# and JUMPBOX_SUBNET_ADDRESS_PREFIX). Set them in your GitHub Environment.
#
# The Bastion subnet name MUST stay "AzureBastionSubnet" (Azure requirement).
# bastion_subnet_name = "AzureBastionSubnet"
#
# Override jumpbox_subnet_name if another namespace already uses the default
# "jumpbox-subnet" in the same spoke VNet.
jumpbox_subnet_name = "nr-ai-form-jumpbox-subnet"

# --- Jumpbox VM ------------------------------------------------------------
vm_size         = "Standard_B2als_v2"
os_disk_type    = "StandardSSD_LRS"
os_disk_size_gb = 64

# --- Toggles ---------------------------------------------------------------
enable_jumpbox            = true
enable_bastion            = true
enable_entra_login        = true
enable_bastion_automation = true  # Auto-shutdown + auto-start runbook

# --- Bastion ---------------------------------------------------------------
bastion_sku                = "Standard"  # Standard required for native client tunneling
bastion_tunneling_enabled  = true
bastion_copy_paste_enabled = true
bastion_file_copy_enabled  = false
bastion_scale_units        = 2

# --- Monitoring (Log Analytics) --------------------------------------------
# The workspace is used only for Bastion connection audit logs (BastionAuditLogs).
# Three modes:
#   1. Create (default, below): a workspace nr-ai-form-law is created automatically.
#   2. Bring your own: set existing_log_analytics_workspace_id (full resource ID).
#   3. Off: set enable_monitoring = false.
enable_monitoring            = true
log_analytics_retention_days = 30
log_analytics_sku            = "PerGB2018"

# Uncomment to attach to an existing workspace instead of creating one:
# existing_log_analytics_workspace_id = "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.OperationalInsights/workspaces/<name>"
