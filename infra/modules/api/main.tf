# API App Service Plan
resource "azurerm_service_plan" "api" {
  name                = "${var.app_name}-api-asp"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.app_service_sku_name_api
  tags                = var.common_tags
  lifecycle {
    ignore_changes = [tags]
  }
}

# API App Service
resource "azurerm_linux_web_app" "api" {
  name                      = "${var.repo_name}-${var.app_env}-api"
  resource_group_name       = var.resource_group_name
  location                  = var.location
  service_plan_id           = azurerm_service_plan.api.id
  https_only                = true
  virtual_network_subnet_id = var.app_service_subnet_id

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on                               = true
    container_registry_use_managed_identity = true
    minimum_tls_version                     = "1.3"
    health_check_path                       = "/health"
    health_check_eviction_time_in_min       = 2
    application_stack {
      docker_image_name   = var.api_image
      docker_registry_url = var.container_registry_url
    }
    ftps_state = "Disabled"
    cors {
      allowed_origins     = ["*"]
      support_credentials = false
    }
    ip_restriction {
      service_tag               = "AzureFrontDoor.Backend"
      ip_address                = null
      virtual_network_subnet_id = null
      action                    = "Allow"
      priority                  = 100
      headers {
        x_azure_fdid      = [var.api_frontdoor_resource_guid]
        x_fd_health_probe = []
        x_forwarded_for   = []
        x_forwarded_host  = []
      }
      name = "Allow traffic from Front Door"
    }
    ip_restriction {
      name        = "DenyAll"
      action      = "Deny"
      priority    = 500
      ip_address  = "0.0.0.0/0"
      description = "Deny all other traffic"
    }
  }
  app_settings = {
    # Python/FastAPI settings
    PORT                                  = "8000"
    WEBSITES_PORT                         = "8000"
    DOCKER_ENABLE_CI                      = "true"
    
    # Application Insights
    APPLICATIONINSIGHTS_CONNECTION_STRING = var.appinsights_connection_string
    APPINSIGHTS_INSTRUMENTATIONKEY        = var.appinsights_instrumentation_key
    
    # Cosmos DB
    COSMOS_DB_ENDPOINT                    = var.cosmosdb_endpoint
    COSMOS_DB_DATABASE_NAME               = var.cosmosdb_db_name
    COSMOS_DB_CONTAINER_NAME              = var.cosmosdb_container_name
    
    # Azure OpenAI Configuration (required for the AI agent)
    AZURE_OPENAI_API_KEY                  = var.azure_openai_api_key
    AZURE_OPENAI_ENDPOINT                 = var.azure_openai_endpoint
    AZURE_OPENAI_API_VERSION              = var.azure_openai_api_version
    AZURE_OPENAI_DEPLOYMENT_NAME          = var.azure_openai_deployment_name
    
    # Azure Search Configuration
    AZURE_SEARCH_ENDPOINT                 = var.azure_search_endpoint
    AZURE_SEARCH_KEY                      = var.azure_search_key
    AZURE_SEARCH_INDEX_NAME               = var.azure_search_index_name
    
    # Azure Document Intelligence Configuration
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT  = var.azure_document_intelligence_endpoint
    AZURE_DOCUMENT_INTELLIGENCE_KEY       = var.azure_document_intelligence_key
    
    # Azure Storage Configuration
    AZURE_STORAGE_ACCOUNT_NAME            = var.azure_storage_account_name
    AZURE_STORAGE_ACCOUNT_KEY             = var.azure_storage_account_key
    AZURE_STORAGE_CONTAINER_NAME          = var.azure_storage_container_name
    
    # Azure App Service specific settings
    WEBSITE_SKIP_RUNNING_KUDUAGENT        = "false"
    WEBSITES_ENABLE_APP_SERVICE_STORAGE   = "false"
    WEBSITE_ENABLE_SYNC_UPDATE_SITE       = "1"
  }
  logs {
    detailed_error_messages = true
    failed_request_tracing  = true
    http_logs {
      file_system {
        retention_in_days = 7
        retention_in_mb   = 100
      }
    }
  }
  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags]
  }
}

# API Autoscaler
resource "azurerm_monitor_autoscale_setting" "api_autoscale" {
  name                = "${var.app_name}-api-autoscale"
  resource_group_name = var.resource_group_name
  location            = var.location
  target_resource_id  = azurerm_service_plan.api.id
  enabled             = var.backend_autoscale_enabled
  profile {
    name = "default"
    capacity {
      default = 2
      minimum = 1
      maximum = 10
    }
    rule {
      metric_trigger {
        metric_name        = "CpuPercentage"
        metric_resource_id = azurerm_service_plan.api.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT5M"
        time_aggregation   = "Average"
        operator           = "GreaterThan"
        threshold          = 70
      }
      scale_action {
        direction = "Increase"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT1M"
      }
    }
    rule {
      metric_trigger {
        metric_name        = "CpuPercentage"
        metric_resource_id = azurerm_service_plan.api.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT5M"
        time_aggregation   = "Average"
        operator           = "LessThan"
        threshold          = 30
      }
      scale_action {
        direction = "Decrease"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT1M"
      }
    }
  }
}
# API Diagnostics
resource "azurerm_monitor_diagnostic_setting" "api_diagnostics" {
  name                       = "${var.app_name}-api-diagnostics"
  target_resource_id         = azurerm_linux_web_app.api.id
  log_analytics_workspace_id = var.log_analytics_workspace_id
  enabled_log {
    category = "AppServiceHTTPLogs"
  }
  enabled_log {
    category = "AppServiceConsoleLogs"
  }
  enabled_log {
    category = "AppServiceAppLogs"
  }
  enabled_log {
    category = "AppServicePlatformLogs"
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

resource "azurerm_cdn_frontdoor_origin" "api_app_service_origin" {
  name                          = "${var.repo_name}-${var.app_env}-api-origin"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.api_origin_group.id

  enabled                        = true
  host_name                      = azurerm_linux_web_app.api.default_hostname
  http_port                      = 80
  https_port                     = 443
  origin_host_header             = azurerm_linux_web_app.api.default_hostname
  priority                       = 1
  weight                         = 1000
  certificate_name_check_enabled = true
}

resource "azurerm_cdn_frontdoor_route" "api_route" {
  name                          = "${var.repo_name}-${var.app_env}-api-fd"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.api_fd_endpoint.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.api_origin_group.id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.api_app_service_origin.id]

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