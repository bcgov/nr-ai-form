# -------------
# Client profile sync (Cosmos DB AgentMemoryDB/ClientProfiles) - enabled when client_profiles_json is set (prod)
# -------------
# The profiles are reviewed in Git (agentic_ai_backend/clientprofiles/prod/clientprofiles.json) and
# passed in by terragrunt/prod/terragrunt.hcl. Cosmos has public network access disabled, so GitHub
# runners cannot write to it; this Container Apps Job runs inside the Container Apps environment (VNet),
# upserts the profiles with its managed identity, and is started after every apply by
# scripts/run-client-profiles-sync.sh (.deployer_aca.yml). A profile change only updates the job's
# secret in place - nothing is replaced, so the prod "no destroy/replace" guard is not tripped.

variable "client_profiles_json" {
  description = "Client profile JSON (object or list) to upsert into Cosmos ClientProfiles. Empty = no sync job."
  type        = string
  default     = ""
}

variable "client_profiles_sync_script" {
  description = "Contents of agentic_ai_backend/clientprofiles/scripts/sync_client_profiles.py, run by the sync job."
  type        = string
  default     = ""
}

locals {
  client_profiles_sync_enabled = var.client_profiles_json != "" && var.client_profiles_sync_script != "" && var.api_backend_image != ""
}

resource "azurerm_container_app_job" "client_profiles_sync" {
  count = local.client_profiles_sync_enabled ? 1 : 0

  name                         = "${var.app_name}-cp-sync"
  location                     = var.location
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = module.container_apps.container_apps_environment_id
  workload_profile_name        = "Consumption"
  replica_timeout_in_seconds   = 600
  replica_retry_limit          = 0

  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }

  identity {
    type = "SystemAssigned"
  }

  secret {
    name  = "client-profiles-json"
    value = var.client_profiles_json
  }

  template {
    container {
      name = "client-profiles-sync"
      # The api-backend image already has azure-cosmos, azure-identity and the clientprofiles
      # package. The script itself comes from this repo (not the image), so promoted test images
      # don't need to contain it.
      image   = var.api_backend_image
      cpu     = 0.25
      memory  = "0.5Gi"
      command = ["sh", "-c"]
      args    = ["printf '%s' \"$SYNC_SCRIPT\" > /tmp/sync_client_profiles.py && python /tmp/sync_client_profiles.py"]

      env {
        name  = "SYNC_SCRIPT"
        value = var.client_profiles_sync_script
      }
      env {
        name        = "CLIENT_PROFILES_JSON"
        secret_name = "client-profiles-json"
      }
      env {
        name  = "AZURE_COSMOS_DB_ENDPOINT"
        value = module.cosmos.cosmosdb_endpoint
      }
      env {
        name  = "AZURE_COSMOS_DB_DATABASE_NAME"
        value = module.cosmos.cosmosdb_sql_database_name
      }
      env {
        name  = "AZURE_COSMOS_DB_CONTAINER_NAME"
        value = module.cosmos.cosmosdb_sql_database_container_name
      }
    }
  }

  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags]
  }
}

# Cosmos DB Built-in Data Contributor, scoped to the ClientProfiles container only.
resource "azurerm_cosmosdb_sql_role_assignment" "client_profiles_sync" {
  count = local.client_profiles_sync_enabled ? 1 : 0

  resource_group_name = azurerm_resource_group.main.name
  account_name        = module.cosmos.account_name
  role_definition_id  = "${module.cosmos.account_id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = azurerm_container_app_job.client_profiles_sync[0].identity[0].principal_id
  scope               = "${module.cosmos.account_id}/dbs/${module.cosmos.cosmosdb_sql_database_name}/colls/${module.cosmos.cosmosdb_sql_database_container_name}"
}

output "client_profiles_sync_job_name" {
  description = "Container Apps Job that upserts client profiles into Cosmos (empty when disabled)."
  value       = local.client_profiles_sync_enabled ? azurerm_container_app_job.client_profiles_sync[0].name : ""
}
