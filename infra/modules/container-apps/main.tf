
resource "azurerm_container_app_environment" "main" {
  name                               = "${var.app_name}-${var.app_env}-containerenv"
  location                           = var.location
  resource_group_name                = var.resource_group_name
  log_analytics_workspace_id         = var.log_analytics_workspace_id
  infrastructure_subnet_id           = var.container_apps_subnet_id
  infrastructure_resource_group_name = "ME-${var.resource_group_name}"      # Changing this will force delete and recreate
  internal_load_balancer_enabled     = true                                 # MUST be true to comply with Azure Policy

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

    container {
      name   = "backend-api"
      image  = var.backend_image
      cpu    = var.container_cpu
      memory = var.container_memory

      # Health probes for the FastAPI backend
      startup_probe {
        transport = "HTTP"
        path      = "/health"
        port      = 8000
        timeout   = 5
      }

      readiness_probe {
        transport               = "HTTP"
        path                    = "/health"
        port                    = 8000
        timeout                 = 5
        failure_count_threshold = 3
      }

      liveness_probe {
        transport               = "HTTP"
        path                    = "/health"
        port                    = 8000
        timeout                 = 5
        failure_count_threshold = 3
      }

      # Application configuration
      env {
        name  = "PORT"
        value = "8000"
      }

      env {
        name  = "LOG_LEVEL"
        value = var.log_level
      }

      # Front Door validation - app can check X-Azure-FDID header matches this
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

    # HTTP scaling rule - scale based on concurrent requests
    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = "20"
    }
  }

  ingress {
    external_enabled           = false # MUST be false - internal only to comply with Azure Policy
    target_port                = 8000
    transport                  = "http"
    allow_insecure_connections = false

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }

    # Internal-only ingress - accessible within VNet
    # Front Door CANNOT connect directly to internal Container Apps
    # Options for public access with Azure Policy:
    # 1. Request Azure Policy exemption for Container Apps (recommended)
    # 2. Use Application Gateway in the VNet as intermediary
    # 3. Upgrade to Front Door Premium + Private Link (expensive)
    # 
    # For now: Container App is internal-only, NOT accessible via Front Door
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
}

resource "azurerm_cdn_frontdoor_origin" "api_container_app_origin" {
  name                          = "${var.repo_name}-${var.app_env}-api-origin"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.api_origin_group.id

  enabled                        = true
  host_name                      = azurerm_container_app.backend.ingress[0].fqdn
  http_port                      = 80
  https_port                     = 443
  origin_host_header             = azurerm_container_app.backend.ingress[0].fqdn
  priority                       = 1
  weight                         = 1000
  certificate_name_check_enabled = true
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
