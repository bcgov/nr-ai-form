
locals {
  # Azure Container App name constraints: ≤32 chars, lowercase alphanumeric + hyphen, no '--'.
  #
  # app_name = "{stack_prefix}-{app_env}" (e.g. "nraii-a3f2-dev" = 14 chars)
  # Adding branch_slug (up to 15) + "-api" (4) would exceed 32 in dev.
  #
  # In dev: strip the trailing "-{app_env}" to reclaim 4 chars, giving:
  #   "{stack_prefix}-{branch_slug}-api"  →  max 10 + 1 + 15 + 4 = 30 chars ✓
  #
  # In test/prod: branch_slug is always "master" (default) and the original
  # name "{app_name}-api" is used unchanged for backward compatibility.
  _app_name_base     = trimsuffix(var.app_name, "-${var.app_env}")
  container_app_name = var.app_env == "dev" ? "${local._app_name_base}-${var.branch_slug}-api" : "${var.app_name}-api"
}

resource "azurerm_container_app_environment" "main" {
  name                       = "${var.app_name}-${var.app_env}-containerenv"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  log_analytics_workspace_id = var.log_analytics_workspace_id
  # infrastructure_subnet_id and its companions must all be set together or all omitted.
  # When no subnet is provided (e.g. dev without a pre-created subnet), omit all three.
  infrastructure_subnet_id           = var.container_apps_subnet_id != "" ? var.container_apps_subnet_id : null
  infrastructure_resource_group_name = var.container_apps_subnet_id != "" ? "ME-${var.resource_group_name}" : null
  internal_load_balancer_enabled     = var.container_apps_subnet_id != "" ? var.internal_load_balancer_enabled : null

  # Azure only accepts Front Door's Private Link connection when public network access is
  # Disabled, so both change together. From this point the *.azurecontainerapps.io URL is
  # blocked from the internet and traffic must come through Front Door.
  public_network_access = local.frontdoor_private_link_enabled ? "Disabled" : "Enabled"

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }

  tags = merge(var.common_tags, {
    Component = "Container Apps Environment"
    Purpose   = "Managed environment for Backend Container Apps"
    Workload  = "Consumption"
  })

  lifecycle {
    ignore_changes = [
      tags,
      # Changing these forces delete-and-recreate; ignore so existing envs are never accidentally replaced
      infrastructure_subnet_id,
      infrastructure_resource_group_name,
      internal_load_balancer_enabled, # Conditionally set based on subnet presence, prevent recreation
    ]
    # The environment is shared across all branch deployments — never let a branch destroy destroy it
    prevent_destroy = true
  }

  logs_destination = "log-analytics"
}

resource "azurerm_private_endpoint" "containerapps" {
  count               = var.internal_load_balancer_enabled ? 1 : 0 # Only create if using internal load balancer
  name                = "${var.app_name}-containerapps-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.app_name}-containerapps-psc"
    private_connection_resource_id = azurerm_container_app_environment.main.id
    subresource_names              = ["managedEnvironments"]
    is_manual_connection           = false
  }

  tags = var.common_tags

  # Lifecycle block to ignore DNS zone group changes managed by Azure Policy
  lifecycle {
    ignore_changes = [
      private_dns_zone_group,
      tags
    ]
  }
}

resource "azurerm_container_app" "backend" {
  name                         = local.container_app_name
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"

  identity {
    type = var.enable_system_assigned_identity ? "SystemAssigned" : "None"
  }

  secret {
    name  = "appinsights-connection-string"
    value = var.appinsights_connection_string
  }

  secret {
    name  = "appinsights-instrumentation-key"
    value = var.appinsights_instrumentation_key
  }

  secret {
    name  = "azure-openai-api-key"
    value = var.azure_openai_api_key
  }

  secret {
    name  = "azure-search-api-key"
    value = var.AZURE_SEARCH_API_KEY
  }

  # Optional: Document Intelligence is used in dev/test only. ACA rejects empty
  # secret values, so the secret is created only when a key is supplied.
  dynamic "secret" {
    for_each = nonsensitive(var.azure_document_intelligence_key != "") ? [1] : []
    content {
      name  = "azure-document-intelligence-key"
      value = var.azure_document_intelligence_key
    }
  }

  secret {
    name  = "azure-storage-account-key"
    value = var.azure_storage_account_key
  }

  secret {
    name  = "azure-blobstorage-connectionstring"
    value = var.azure_blobstorage_connectionstring
  }

  # Optional: without a key (prod) the api-backend authenticates to Cosmos with this
  # Container App's managed identity (DefaultAzureCredential in clientprofiles/factory.py).
  # ACA rejects empty secret values, so the secret is created only when a key is supplied.
  dynamic "secret" {
    for_each = nonsensitive(var.azure_cosmos_db_key != "") ? [1] : []
    content {
      name  = "azure-cosmos-db-key"
      value = var.azure_cosmos_db_key
    }
  }

  secret {
    name  = "redis-password"
    value = var.redis_password
  }

  template {
    max_replicas                     = var.max_replicas
    min_replicas                     = var.min_replicas
    termination_grace_period_seconds = 10

    # Orchestrator Agent Container - Main Application
    container {
      name   = "orchestrator-agent"
      image  = var.orchestrator_agent_image != "" ? var.orchestrator_agent_image : var.backend_image
      cpu    = var.container_cpu
      memory = var.container_memory

      # Health probes for Orchestrator Agent
      startup_probe {
        transport = "HTTP"
        path      = "/health"
        port      = var.orchestrator_agent_port
        timeout   = 5
      }

      readiness_probe {
        transport               = "HTTP"
        path                    = "/health"
        port                    = var.orchestrator_agent_port
        timeout                 = 5
        failure_count_threshold = 3
      }

      liveness_probe {
        transport               = "HTTP"
        path                    = "/health"
        port                    = var.orchestrator_agent_port
        timeout                 = 5
        failure_count_threshold = 3
      }

      # Environment variables for Orchestrator Agent
      env {
        name  = "PORT"
        value = tostring(var.orchestrator_agent_port)
      }

      # env {
      #   name  = "LOG_LEVEL"
      #   value = var.log_level
      # }

      # A2A URLs - use localhost since all containers are in the same pod
      env {
        name  = "CONVERSATION_AGENT_A2A_URL"
        value = "http://localhost:${var.conversation_agent_port}"
      }

      env {
        name  = "FORM_SUPPORT_AGENT_A2A_URL"
        value = "http://localhost:${var.formsupport_agent_port}"
      }

      # Application Insights
      env {
        name        = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        secret_name = "appinsights-connection-string"
      }

      env {
        name        = "APPINSIGHTS_INSTRUMENTATIONKEY"
        secret_name = "appinsights-instrumentation-key"
      }

      # Azure OpenAI Configuration
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-api-key"
      }

      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = var.azure_openai_endpoint
      }

      # Azure Blob Storage Configuration
      env {
        name        = "AZURE_BLOBSTORAGE_CONNECTIONSTRING"
        secret_name = "azure-blobstorage-connectionstring"
      }

      env {
        name  = "AZURE_BLOBSTORAGE_CONTAINER"
        value = var.azure_blobstorage_container
      }

      # Orchestrator Prompt Cache Configuration
      env {
        name  = "ORCHESTRATOR_PROMPT_CACHE_TTL_SECONDS"
        value = tostring(var.orchestrator_prompt_cache_ttl_seconds)
      }

      # Redis Configuration
      env {
        name  = "REDIS_HOST"
        value = var.redis_host
      }

      env {
        name  = "REDIS_PORT"
        value = tostring(var.redis_port)
      }

      env {
        name        = "REDIS_PASSWORD"
        secret_name = "redis-password"
      }

      env {
        name  = "REDIS_SSL"
        value = tostring(var.redis_ssl)
      }

      env {
        name  = "REDIS_TTL_DAYS"
        value = tostring(var.redis_ttl_days)
      }
    }

    # Conversation Agent Container - Sidecar 1
    container {
      name   = "conversation-agent"
      image  = var.conversation_agent_image != "" ? var.conversation_agent_image : ""
      cpu    = var.container_cpu
      memory = var.container_memory

      # Health probes for Conversation Agent
      startup_probe {
        transport = "HTTP"
        path      = "/health"
        port      = var.conversation_agent_port
        timeout   = 5
      }

      readiness_probe {
        transport               = "HTTP"
        path                    = "/health"
        port                    = var.conversation_agent_port
        timeout                 = 5
        failure_count_threshold = 3
      }

      liveness_probe {
        transport               = "HTTP"
        path                    = "/health"
        port                    = var.conversation_agent_port
        timeout                 = 5
        failure_count_threshold = 3
      }

      # Environment variables for Conversation Agent
      env {
        name  = "PORT"
        value = tostring(var.conversation_agent_port)
      }

      env {
        name  = "HOST"
        value = "0.0.0.0"
      }

      # Application Insights
      env {
        name        = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        secret_name = "appinsights-connection-string"
      }

      env {
        name        = "APPINSIGHTS_INSTRUMENTATIONKEY"
        secret_name = "appinsights-instrumentation-key"
      }

      # Azure OpenAI Configuration
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-api-key"
      }

      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = var.azure_openai_endpoint
      }

      # Azure Search Configuration
      env {
        name  = "AZURE_SEARCH_ENDPOINT"
        value = var.azure_search_endpoint
      }

      env {
        name        = "AZURE_SEARCH_API_KEY"
        secret_name = "azure-search-api-key"
      }

      # Azure Blob Storage Configuration
      env {
        name        = "AZURE_BLOBSTORAGE_CONNECTIONSTRING"
        secret_name = "azure-blobstorage-connectionstring"
      }

      env {
        name  = "AZURE_BLOBSTORAGE_CONTAINER"
        value = var.azure_blobstorage_container
      }

      # Conversation Agent Prompt Cache Configuration
      env {
        name  = "CONVERSATION_PROMPT_CACHE_TTL_SECONDS"
        value = tostring(var.conversation_prompt_cache_ttl_seconds)
      }
    }

    # Form Support Agent Container - Sidecar 2
    container {
      name   = "formsupport-agent"
      image  = var.formsupport_agent_image != "" ? var.formsupport_agent_image : ""
      cpu    = var.container_cpu
      memory = var.container_memory

      # Health probes for Form Support Agent
      startup_probe {
        transport = "HTTP"
        path      = "/health"
        port      = var.formsupport_agent_port
        timeout   = 5
      }

      readiness_probe {
        transport               = "HTTP"
        path                    = "/health"
        port                    = var.formsupport_agent_port
        timeout                 = 5
        failure_count_threshold = 3
      }

      liveness_probe {
        transport               = "HTTP"
        path                    = "/health"
        port                    = var.formsupport_agent_port
        timeout                 = 5
        failure_count_threshold = 3
      }

      # Environment variables for Form Support Agent
      env {
        name  = "PORT"
        value = tostring(var.formsupport_agent_port)
      }

      env {
        name  = "HOST"
        value = "0.0.0.0"
      }

      # Application Insights
      env {
        name        = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        secret_name = "appinsights-connection-string"
      }

      env {
        name        = "APPINSIGHTS_INSTRUMENTATIONKEY"
        secret_name = "appinsights-instrumentation-key"
      }

      # Azure OpenAI Configuration
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-api-key"
      }

      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = var.azure_openai_endpoint
      }

      # Azure Blob Storage Configuration
      env {
        name        = "AZURE_BLOBSTORAGE_CONNECTIONSTRING"
        secret_name = "azure-blobstorage-connectionstring"
      }

      env {
        name  = "AZURE_BLOBSTORAGE_CONTAINER"
        value = var.azure_blobstorage_container
      }

      # Form Support Agent Cache Configuration
      env {
        name  = "FORM_SUPPORT_AGENT_CACHE_TTL_SECONDS"
        value = tostring(var.form_support_agent_cache_ttl_seconds)
      }

      env {
        name  = "FORM_SUPPORT_PROMPT_CACHE_TTL_SECONDS"
        value = tostring(var.form_support_prompt_cache_ttl_seconds)
      }

      env {
        name  = "FORM_SUPPORT_ASSET_CACHE_TTL_SECONDS"
        value = tostring(var.form_support_asset_cache_ttl_seconds)
      }
    }
    
    # API Backend Container - Public-facing WebSocket gateway to orchestrator
    # Only deploy if api_backend_image is provided
    dynamic "container" {
      for_each = var.api_backend_image != "" ? [1] : []
      content {
        name   = "api-backend"
        image  = var.api_backend_image
        cpu    = var.container_cpu
        memory = var.container_memory

        startup_probe {
          transport = "HTTP"
          path      = "/health"
          port      = var.api_backend_port
          timeout   = 5
        }

        readiness_probe {
          transport               = "HTTP"
          path                    = "/health"
          port                    = var.api_backend_port
          timeout                 = 5
          failure_count_threshold = 3
        }

        liveness_probe {
          transport               = "HTTP"
          path                    = "/health"
          port                    = var.api_backend_port
          timeout                 = 5
          failure_count_threshold = 3
        }

        env {
          name  = "PORT"
          value = tostring(var.api_backend_port)
        }

        env {
          name  = "ORCHESTRATOR_AGENT_WS_URL"
          # Containers in one Container App share a network namespace: reach the orchestrator on localhost
          # (container names are not DNS names in ACA, unlike docker-compose).
          value = "ws://localhost:${var.orchestrator_agent_port}/ws"
        }

        env {
          name  = "AZURE_COSMOS_DB_ENDPOINT"
          value = var.azure_cosmos_db_endpoint
        }

        dynamic "env" {
          for_each = nonsensitive(var.azure_cosmos_db_key != "") ? [1] : []
          content {
            name        = "AZURE_COSMOS_DB_KEY"
            secret_name = "azure-cosmos-db-key"
          }
        }

        env {
          name  = "AZURE_COSMOS_DB_DATABASE_NAME"
          value = var.azure_cosmos_db_database_name
        }

        env {
          name  = "TENANT_PROFILE_FRESH_TTL_SECONDS"
          value = tostring(var.tenant_profile_fresh_ttl_seconds)
        }

        env {
          name  = "TENANT_PROFILE_STALE_TTL_SECONDS"
          value = tostring(var.tenant_profile_stale_ttl_seconds)
        }

        env {
          name  = "TENANT_PROFILE_LOOKUP_TIMEOUT_SECONDS"
          value = tostring(var.tenant_profile_lookup_timeout_seconds)
        }

        env {
          name  = "REDIS_HOST"
          value = var.redis_host
        }

        env {
          name  = "REDIS_PORT"
          value = tostring(var.redis_port)
        }

        env {
          name        = "REDIS_PASSWORD"
          secret_name = "redis-password"
        }

        env {
          name  = "REDIS_SSL"
          value = tostring(var.redis_ssl)
        }

        env {
          name  = "REDIS_TTL_DAYS"
          value = tostring(var.redis_ttl_days)
        }
      }
    }

    # HTTP scaling rule - scale based on concurrent requests
    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = "20"
    }
  }

  ingress {
    external_enabled           = true                        # Must be true for Front Door to reach the public endpoint
    target_port                = var.api_backend_image != "" ? var.api_backend_port : var.orchestrator_agent_port # If api_backend is deployed, it's the public-facing endpoint; otherwise orchestrator is
    transport                  = "auto"                      # Allows HTTPS from Front Door, HTTP internally
    allow_insecure_connections = false

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = merge(var.common_tags, {
    Component = "Backend Container App"
    Purpose   = "NR AI Form API Backend"
    Workload  = "Consumption"
  })

  lifecycle {
    ignore_changes = [tags]
  }

  depends_on = [azurerm_container_app_environment.main]
}


resource "azurerm_monitor_diagnostic_setting" "container_app_env_diagnostics" {
  name                       = "${var.app_name}-ca-env-diagnostics"
  target_resource_id         = azurerm_container_app_environment.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category_group = "allLogs"
  }

  enabled_log {
    category_group = "audit"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

resource "azurerm_monitor_diagnostic_setting" "backend_container_app_diagnostics" {
  name                       = "${var.app_name}-backend-ca-diagnostics"
  target_resource_id         = azurerm_container_app.backend.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_metric {
    category = "AllMetrics"
  }
}



# Normalize the FQDN by removing the .internal prefix that Azure adds during apply
locals {
  backend_fqdn = replace(azurerm_container_app.backend.ingress[0].fqdn, ".internal.", ".")
}

# All Front Door / CDN resources below are only created when enable_front_door = true
resource "azurerm_cdn_frontdoor_endpoint" "api_fd_endpoint" {
  count                    = var.enable_front_door ? 1 : 0
  name                     = "${var.repo_name}-${var.app_env}-api-fd"
  cdn_frontdoor_profile_id = var.api_frontdoor_id
}

resource "azurerm_cdn_frontdoor_origin_group" "api_origin_group" {
  count                    = var.enable_front_door ? 1 : 0
  name                     = "${var.repo_name}-${var.app_env}-api-origin-group"
  cdn_frontdoor_profile_id = var.api_frontdoor_id
  session_affinity_enabled = true

  load_balancing {
    sample_size                 = 4
    successful_samples_required = 3
  }

  health_probe {
    interval_in_seconds = 100
    path                = "/health"
    protocol            = "Http"
    request_type        = "GET"
  }
}

resource "azurerm_cdn_frontdoor_origin" "api_container_app_origin" {
  count                         = var.enable_front_door ? 1 : 0
  name                          = "${var.repo_name}-${var.app_env}-api-origin"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.api_origin_group[0].id

  host_name                      = local.backend_fqdn
  http_port                      = 8002
  https_port                     = 443
  origin_host_header             = local.backend_fqdn
  priority                       = 1
  weight                         = 1000
  certificate_name_check_enabled = true

  # Public origin. When Front Door uses Private Link (prod) it is kept but disabled instead of
  # deleted: adding private_link to an origin forces a replace, and Azure refuses to delete the
  # last origin of a group that a route uses. It is disabled only after the Private Link origin
  # below exists (depends_on), since Azure also refuses to disable the last enabled origin.
  enabled = !local.frontdoor_private_link_enabled

  # Ignore changes to host_name and origin_host_header due to Azure provider
  # inconsistency when Container App has internal ingress enabled.
  # The provider reports different FQDN values during plan vs apply.
  lifecycle {
    ignore_changes = [host_name, origin_host_header]
  }

  depends_on = [azurerm_container_app.backend, azurerm_cdn_frontdoor_origin.api_container_app_origin_private_link]
}

# Front Door Premium reaches the Container Apps environment over Private Link (prod). Azure only
# accepts this when the environment's public network access is Disabled; referencing the
# environment makes Terraform apply that change first. The resulting private endpoint connection
# is approved by terraform_data.approve_frontdoor_private_link below.
resource "azurerm_cdn_frontdoor_origin" "api_container_app_origin_private_link" {
  count                         = local.frontdoor_private_link_enabled ? 1 : 0
  name                          = "${var.repo_name}-${var.app_env}-api-origin-pl"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.api_origin_group[0].id

  enabled                        = true
  host_name                      = local.backend_fqdn
  http_port                      = 80
  https_port                     = 443
  origin_host_header             = local.backend_fqdn
  priority                       = 1
  weight                         = 1000
  certificate_name_check_enabled = true

  private_link {
    request_message        = local.frontdoor_private_link_request_message
    target_type            = "managedEnvironments"
    location               = var.location
    private_link_target_id = azurerm_container_app_environment.main.id
  }

  lifecycle {
    ignore_changes = [host_name, origin_host_header]
  }

  depends_on = [azurerm_container_app.backend]
}

resource "azurerm_cdn_frontdoor_route" "api_route" {
  count                         = var.enable_front_door ? 1 : 0
  name                          = "${var.repo_name}-${var.app_env}-api-fd"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.api_fd_endpoint[0].id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.api_origin_group[0].id
  cdn_frontdoor_origin_ids = concat(
    [azurerm_cdn_frontdoor_origin.api_container_app_origin[0].id],
    azurerm_cdn_frontdoor_origin.api_container_app_origin_private_link[*].id,
  )

  supported_protocols    = ["Http", "Https"]
  patterns_to_match      = ["/*"]
  forwarding_protocol    = "HttpsOnly"
  link_to_default_domain = true
  https_redirect_enabled = true
}

locals {
  frontdoor_private_link_enabled         = var.enable_front_door && var.api_frontdoor_private_link_enabled
  frontdoor_private_link_request_message = "Azure Front Door ${var.app_name} access to Container Apps"
}

# Front Door's Private Link request arrives as Pending on the Container Apps environment and
# azurerm cannot approve it, so approve it with the az CLI (logged in by azure/login in
# .deployer_aca.yml), as is done for the Search -> Storage shared private link in infra/main.tf.
# Front Door creates the request asynchronously after the origin update, so this waits for it.
# Only approves connections carrying our request message.
resource "terraform_data" "approve_frontdoor_private_link" {
  count            = local.frontdoor_private_link_enabled ? 1 : 0
  triggers_replace = [azurerm_cdn_frontdoor_origin.api_container_app_origin_private_link[0].id, local.frontdoor_private_link_request_message]

  provisioner "local-exec" {
    interpreter = ["bash", "-c"]
    environment = {
      ENV_ID           = azurerm_container_app_environment.main.id
      REQUEST_MESSAGE  = local.frontdoor_private_link_request_message
      APPROVED_MESSAGE = "Approved by Terraform for Azure Front Door"
      API_VERSION      = "2024-10-02-preview"
      MSYS_NO_PATHCONV = "1" # Git Bash on Windows would otherwise rewrite /subscriptions/... into a file path
    }
    command = <<-EOT
      set -euo pipefail
      url="https://management.azure.com$ENV_ID/privateEndpointConnections?api-version=$API_VERSION"
      for attempt in $(seq 1 40); do
        conns=$(az rest --method get --url "$url" \
          --query "value[?properties.privateLinkServiceConnectionState.description=='$REQUEST_MESSAGE' || properties.privateLinkServiceConnectionState.description=='$APPROVED_MESSAGE'].{id:id,status:properties.privateLinkServiceConnectionState.status}" \
          -o tsv | tr -d '\r')
        if echo "$conns" | grep -q $'\tApproved$' && ! echo "$conns" | grep -q $'\tPending$'; then
          echo "Front Door private endpoint connection already approved."
          exit 0
        fi
        pending=$(echo "$conns" | awk -F'\t' '$2=="Pending"{print $1}')
        if [ -n "$pending" ]; then
          for id in $pending; do
            echo "Approving $id"
            az rest --method put --url "https://management.azure.com$id?api-version=$API_VERSION" \
              --body '{"properties":{"privateLinkServiceConnectionState":{"status":"Approved","description":"'"$APPROVED_MESSAGE"'"}}}' > /dev/null
          done
          exit 0
        fi
        echo "Waiting for Front Door private endpoint connection request ($attempt/40)..."
        sleep 15
      done
      echo "No Front Door private endpoint connection request appeared on $ENV_ID within 10 minutes." >&2
      exit 1
    EOT
  }
}

resource "azurerm_cdn_frontdoor_security_policy" "frontend_fd_security_policy" {
  count                    = var.enable_front_door ? 1 : 0
  name                     = "${var.app_name}-api-fd-waf-security-policy"
  cdn_frontdoor_profile_id = var.api_frontdoor_id

  security_policies {
    firewall {
      cdn_frontdoor_firewall_policy_id = var.api_frontdoor_firewall_policy_id

      association {
        domain {
          cdn_frontdoor_domain_id = azurerm_cdn_frontdoor_endpoint.api_fd_endpoint[0].id
        }
        patterns_to_match = ["/*"]
      }
    }
  }
}