
resource "azurerm_container_app_environment" "main" {
  name                               = "${var.app_name}-${var.app_env}-containerenv"
  location                           = var.location
  resource_group_name                = var.resource_group_name
  log_analytics_workspace_id         = var.log_analytics_workspace_id
  infrastructure_subnet_id           = var.container_apps_subnet_id
  infrastructure_resource_group_name = "ME-${var.resource_group_name}" # Changing this will force delete and recreate
  internal_load_balancer_enabled     = true                            # MUST be true to comply with Azure Policy

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
    ignore_changes = [tags]
  }

  logs_destination = "log-analytics"
}

resource "azurerm_private_endpoint" "containerapps" {
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
  name                         = "${var.app_name}-api"
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
    name  = "azure-search-key"
    value = var.azure_search_key
  }

  secret {
    name  = "azure-document-intelligence-key"
    value = var.azure_document_intelligence_key
  }

  secret {
    name  = "azure-storage-account-key"
    value = var.azure_storage_account_key
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

      env {
        name  = "LOG_LEVEL"
        value = var.log_level
      }

      # A2A URLs - use localhost since all containers are in the same pod
      env {
        name  = "CONVERSATION_AGENT_A2A_URL"
        value = "http://localhost:${var.conversation_agent_port}"
      }

      env {
        name  = "FORM_SUPPORT_AGENT_A2A_URL"
        value = "http://localhost:${var.formsupport_agent_port}"
      }

      # Front Door validation
      env {
        name  = "AZURE_FRONTDOOR_ID"
        value = var.api_frontdoor_resource_guid
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

      # Cosmos DB Configuration
      env {
        name  = "COSMOS_DB_ENDPOINT"
        value = var.cosmosdb_endpoint
      }

      env {
        name  = "COSMOS_DB_DATABASE_NAME"
        value = var.cosmosdb_db_name
      }

      env {
        name  = "COSMOS_DB_CONTAINER_NAME"
        value = var.cosmosdb_container_name
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

      env {
        name  = "AZURE_OPENAI_API_VERSION"
        value = var.azure_openai_api_version
      }

      env {
        name  = "AZURE_OPENAI_DEPLOYMENT_NAME"
        value = var.azure_openai_deployment_name
      }

      # Azure Search Configuration
      env {
        name  = "AZURE_SEARCH_ENDPOINT"
        value = var.azure_search_endpoint
      }

      env {
        name        = "AZURE_SEARCH_KEY"
        secret_name = "azure-search-key"
      }

      env {
        name  = "AZURE_SEARCH_INDEX_NAME"
        value = var.azure_search_index_name
      }

      # Azure Document Intelligence Configuration
      env {
        name  = "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
        value = var.azure_document_intelligence_endpoint
      }

      env {
        name        = "AZURE_DOCUMENT_INTELLIGENCE_KEY"
        secret_name = "azure-document-intelligence-key"
      }

      # Azure Storage Configuration
      env {
        name  = "AZURE_STORAGE_ACCOUNT_NAME"
        value = var.azure_storage_account_name
      }

      env {
        name        = "AZURE_STORAGE_ACCOUNT_KEY"
        secret_name = "azure-storage-account-key"
      }

      env {
        name  = "AZURE_STORAGE_CONTAINER_NAME"
        value = var.azure_storage_container_name
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
        name  = "LOG_LEVEL"
        value = var.log_level
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

      # Cosmos DB Configuration
      env {
        name  = "COSMOS_DB_ENDPOINT"
        value = var.cosmosdb_endpoint
      }

      env {
        name  = "COSMOS_DB_DATABASE_NAME"
        value = var.cosmosdb_db_name
      }

      env {
        name  = "COSMOS_DB_CONTAINER_NAME"
        value = var.cosmosdb_container_name
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

      env {
        name  = "AZURE_OPENAI_API_VERSION"
        value = var.azure_openai_api_version
      }

      env {
        name  = "AZURE_OPENAI_DEPLOYMENT_NAME"
        value = var.azure_openai_deployment_name
      }

      # Azure Search Configuration
      env {
        name  = "AZURE_SEARCH_ENDPOINT"
        value = var.azure_search_endpoint
      }

      env {
        name        = "AZURE_SEARCH_KEY"
        secret_name = "azure-search-key"
      }

      env {
        name  = "AZURE_SEARCH_INDEX_NAME"
        value = var.azure_search_index_name
      }

      # Azure Document Intelligence Configuration
      env {
        name  = "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
        value = var.azure_document_intelligence_endpoint
      }

      env {
        name        = "AZURE_DOCUMENT_INTELLIGENCE_KEY"
        secret_name = "azure-document-intelligence-key"
      }

      # Azure Storage Configuration
      env {
        name  = "AZURE_STORAGE_ACCOUNT_NAME"
        value = var.azure_storage_account_name
      }

      env {
        name        = "AZURE_STORAGE_ACCOUNT_KEY"
        secret_name = "azure-storage-account-key"
      }

      env {
        name  = "AZURE_STORAGE_CONTAINER_NAME"
        value = var.azure_storage_container_name
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
        name  = "LOG_LEVEL"
        value = var.log_level
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

      # Cosmos DB Configuration
      env {
        name  = "COSMOS_DB_ENDPOINT"
        value = var.cosmosdb_endpoint
      }

      env {
        name  = "COSMOS_DB_DATABASE_NAME"
        value = var.cosmosdb_db_name
      }

      env {
        name  = "COSMOS_DB_CONTAINER_NAME"
        value = var.cosmosdb_container_name
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

      env {
        name  = "AZURE_OPENAI_API_VERSION"
        value = var.azure_openai_api_version
      }

      env {
        name  = "AZURE_OPENAI_DEPLOYMENT_NAME"
        value = var.azure_openai_deployment_name
      }

      # Azure Search Configuration
      env {
        name  = "AZURE_SEARCH_ENDPOINT"
        value = var.azure_search_endpoint
      }

      env {
        name        = "AZURE_SEARCH_KEY"
        secret_name = "azure-search-key"
      }

      env {
        name  = "AZURE_SEARCH_INDEX_NAME"
        value = var.azure_search_index_name
      }

      # Azure Document Intelligence Configuration
      env {
        name  = "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
        value = var.azure_document_intelligence_endpoint
      }

      env {
        name        = "AZURE_DOCUMENT_INTELLIGENCE_KEY"
        secret_name = "azure-document-intelligence-key"
      }

      # Azure Storage Configuration
      env {
        name  = "AZURE_STORAGE_ACCOUNT_NAME"
        value = var.azure_storage_account_name
      }

      env {
        name        = "AZURE_STORAGE_ACCOUNT_KEY"
        secret_name = "azure-storage-account-key"
      }

      env {
        name  = "AZURE_STORAGE_CONTAINER_NAME"
        value = var.azure_storage_container_name
      }
    }

    # HTTP scaling rule - scale based on concurrent requests
    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = "20"
    }
  }

  ingress {
    external_enabled           = true # Must be true for Front Door to reach the backend
    target_port                = 8002 # Backend app runs on port 8002
    transport                  = "auto" # Allows HTTPS from Front Door, HTTP internally
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



resource "azurerm_cdn_frontdoor_endpoint" "api_fd_endpoint" {
  name                     = "${var.repo_name}-${var.app_env}-api-fd"
  cdn_frontdoor_profile_id = var.api_frontdoor_id
}

resource "azurerm_cdn_frontdoor_origin_group" "api_origin_group" {
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
    protocol            = "Https"
    request_type        = "GET"
  }
}

# Normalize the FQDN by removing the .internal prefix that Azure adds during apply
locals {
  backend_fqdn = replace(azurerm_container_app.backend.ingress[0].fqdn, ".internal.", ".")
}

resource "azurerm_cdn_frontdoor_origin" "api_container_app_origin" {
  name                          = "${var.repo_name}-${var.app_env}-api-origin"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.api_origin_group.id

  enabled                        = true
  host_name                      = local.backend_fqdn
  http_port                      = 80
  https_port                     = 443
  origin_host_header             = local.backend_fqdn
  priority                       = 1
  weight                         = 1000
  certificate_name_check_enabled = true

  # Ignore changes to host_name and origin_host_header due to Azure provider
  # inconsistency when Container App has internal ingress enabled.
  # The provider reports different FQDN values during plan vs apply.
  lifecycle {
    ignore_changes = [host_name, origin_host_header]
  }

  depends_on = [azurerm_container_app.backend]
}

resource "azurerm_cdn_frontdoor_route" "api_route" {
  name                          = "${var.repo_name}-${var.app_env}-api-fd"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.api_fd_endpoint.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.api_origin_group.id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.api_container_app_origin.id]

  supported_protocols    = ["Http", "Https"]
  patterns_to_match      = ["/*"]
  forwarding_protocol    = "HttpsOnly"
  link_to_default_domain = true
  https_redirect_enabled = true
}

resource "azurerm_cdn_frontdoor_security_policy" "frontend_fd_security_policy" {
  name                     = "${var.app_name}-api-fd-waf-security-policy"
  cdn_frontdoor_profile_id = var.api_frontdoor_id

  security_policies {
    firewall {
      cdn_frontdoor_firewall_policy_id = var.api_frontdoor_firewall_policy_id

      association {
        domain {
          cdn_frontdoor_domain_id = azurerm_cdn_frontdoor_endpoint.api_fd_endpoint.id
        }
        patterns_to_match = ["/*"]
      }
    }
  }
}
