
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
      internal_load_balancer_enabled,  # Conditionally set based on subnet presence, prevent recreation
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

  secret {
    name  = "azure-document-intelligence-key"
    value = var.azure_document_intelligence_key
  }

  secret {
    name  = "azure-storage-account-key"
    value = var.azure_storage_account_key
  }

  secret {
    name  = "azure-blobstorage-connectionstring"
    value = var.azure_blobstorage_connectionstring
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

      # Front Door validation (empty when Front Door is disabled)
      env {
        name  = "AZURE_FRONTDOOR_ID"
        value = var.enable_front_door ? var.api_frontdoor_resource_guid : ""
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

      # Cosmos DB Configuration (only set when value provided)
      dynamic "env" {
        for_each = var.cosmosdb_endpoint != "" ? [var.cosmosdb_endpoint] : []
        content {
          name  = "COSMOS_DB_ENDPOINT"
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.cosmosdb_db_name != "" ? [var.cosmosdb_db_name] : []
        content {
          name  = "COSMOS_DB_DATABASE_NAME"
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.cosmosdb_container_name != "" ? [var.cosmosdb_container_name] : []
        content {
          name  = "COSMOS_DB_CONTAINER_NAME"
          value = env.value
        }
      }

      # Inject additional orchestrator-specific env vars from a map
      dynamic "env" {
        for_each = var.orchestrator_env
        content {
          name  = env.key
          value = env.value
        }
      }

      # Azure OpenAI Configuration
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-api-key"
      }

      dynamic "env" {
        for_each = var.azure_openai_endpoint != "" ? [var.azure_openai_endpoint] : []
        content {
          name  = "AZURE_OPENAI_ENDPOINT"
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.azure_openai_api_version != "" ? [var.azure_openai_api_version] : []
        content {
          name  = "AZURE_OPENAI_API_VERSION"
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME != "" ? [var.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME] : []
        content {
          name  = "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
          value = env.value
        }
      }

      # Azure Search Configuration
      dynamic "env" {
        for_each = var.azure_search_endpoint != "" ? [var.azure_search_endpoint] : []
        content {
          name  = "AZURE_SEARCH_ENDPOINT"
          value = env.value
        }
      }

      env {
        name        = "AZURE_SEARCH_API_KEY"
        secret_name = "azure-search-api-key"
      }

      dynamic "env" {
        for_each = var.azure_search_index_name != "" ? [var.azure_search_index_name] : []
        content {
          name  = "AZURE_SEARCH_INDEX_NAME"
          value = env.value
        }
      }

      env {
        name  = "AZURE_SEARCH_TOP"
        value = tostring(var.azure_search_top)
      }

      env {
        name  = "AZURE_SEARCH_TRIM_LENGTH"
        value = tostring(var.azure_search_trim_length)
      }

      env {
        name  = "AZURE_SEARCH_ENABLE_TRIMMING"
        value = tostring(var.azure_search_enable_trimming)
      }

      env {
        name  = "AZURE_SEARCH_INCLUDE_TOTAL_COUNT"
        value = tostring(var.azure_search_include_total_count)
      }

      env {
        name  = "AZURE_SEARCH_QUERY_TYPE"
        value = var.azure_search_query_type
      }

      env {
        name  = "AZURE_SEARCH_SEMANTIC_CONFIGURATION"
        value = var.azure_search_semantic_configuration
      }

      env {
        name  = "AZURE_SEARCH_QUERY_CAPTION"
        value = var.azure_search_query_caption
      }

      env {
        name  = "AZURE_SEARCH_QUERY_ANSWER"
        value = var.azure_search_query_answer
      }

      env {
        name  = "AZURE_SEARCH_QUERY_ANSWER_COUNT"
        value = tostring(var.azure_search_query_answer_count)
      }

      env {
        name  = "AZURE_SEARCH_QUERY_LANGUAGE"
        value = var.azure_search_query_language
      }

      # Agent Configuration
      env {
        name  = "AGENT_TEMPERATURE"
        value = tostring(var.agent_temperature)
      }

      env {
        name  = "AGENT_MAX_TOKENS"
        value = tostring(var.agent_max_tokens)
      }

      # Azure Document Intelligence Configuration
      dynamic "env" {
        for_each = var.azure_document_intelligence_endpoint != "" ? [var.azure_document_intelligence_endpoint] : []
        content {
          name  = "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
          value = env.value
        }
      }

      env {
        name        = "AZURE_DOCUMENT_INTELLIGENCE_KEY"
        secret_name = "azure-document-intelligence-key"
      }

      # Azure Storage Configuration
      dynamic "env" {
        for_each = var.azure_storage_account_name != "" ? [var.azure_storage_account_name] : []
        content {
          name  = "AZURE_STORAGE_ACCOUNT_NAME"
          value = env.value
        }
      }

      env {
        name        = "AZURE_STORAGE_ACCOUNT_KEY"
        secret_name = "azure-storage-account-key"
      }

      env {
        name  = "AZURE_STORAGE_CONTAINER_NAME"
        value = var.azure_storage_container_name
      }

      # Azure Blob Storage Configuration
      env {
        name        = "AZURE_BLOBSTORAGE_CONNECTIONSTRING"
        secret_name = "azure-blobstorage-connectionstring"
      }

      dynamic "env" {
        for_each = var.azure_blobstorage_container != "" ? [var.azure_blobstorage_container] : []
        content {
          name  = "AZURE_BLOBSTORAGE_CONTAINER"
          value = env.value
        }
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

      env {
        name  = "CORS_ALLOW_ORIGINS"
        value = tostring(var.cors_allow_origins)
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

      # Cosmos DB Configuration (only set when value provided)
      dynamic "env" {
        for_each = var.cosmosdb_endpoint != "" ? [var.cosmosdb_endpoint] : []
        content {
          name  = "COSMOS_DB_ENDPOINT"
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.cosmosdb_db_name != "" ? [var.cosmosdb_db_name] : []
        content {
          name  = "COSMOS_DB_DATABASE_NAME"
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.cosmosdb_container_name != "" ? [var.cosmosdb_container_name] : []
        content {
          name  = "COSMOS_DB_CONTAINER_NAME"
          value = env.value
        }
      }

      # Azure OpenAI Configuration
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-api-key"
      }

      dynamic "env" {
        for_each = var.azure_openai_endpoint != "" ? [var.azure_openai_endpoint] : []
        content {
          name  = "AZURE_OPENAI_ENDPOINT"
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.azure_openai_api_version != "" ? [var.azure_openai_api_version] : []
        content {
          name  = "AZURE_OPENAI_API_VERSION"
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME != "" ? [var.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME] : []
        content {
          name  = "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
          value = env.value
        }
      }

      # Azure Search Configuration
      dynamic "env" {
        for_each = var.azure_search_endpoint != "" ? [var.azure_search_endpoint] : []
        content {
          name  = "AZURE_SEARCH_ENDPOINT"
          value = env.value
        }
      }

      env {
        name        = "AZURE_SEARCH_API_KEY"
        secret_name = "azure-search-api-key"
      }

      dynamic "env" {
        for_each = var.azure_search_index_name != "" ? [var.azure_search_index_name] : []
        content {
          name  = "AZURE_SEARCH_INDEX_NAME"
          value = env.value
        }
      }

      env {
        name  = "AZURE_SEARCH_TOP"
        value = tostring(var.azure_search_top)
      }

      env {
        name  = "AZURE_SEARCH_TRIM_LENGTH"
        value = tostring(var.azure_search_trim_length)
      }

      env {
        name  = "AZURE_SEARCH_ENABLE_TRIMMING"
        value = tostring(var.azure_search_enable_trimming)
      }

      env {
        name  = "AZURE_SEARCH_INCLUDE_TOTAL_COUNT"
        value = tostring(var.azure_search_include_total_count)
      }

      env {
        name  = "AZURE_SEARCH_QUERY_TYPE"
        value = var.azure_search_query_type
      }

      env {
        name  = "AZURE_SEARCH_SEMANTIC_CONFIGURATION"
        value = var.azure_search_semantic_configuration
      }

      env {
        name  = "AZURE_SEARCH_QUERY_CAPTION"
        value = var.azure_search_query_caption
      }

      env {
        name  = "AZURE_SEARCH_QUERY_ANSWER"
        value = var.azure_search_query_answer
      }

      env {
        name  = "AZURE_SEARCH_QUERY_ANSWER_COUNT"
        value = tostring(var.azure_search_query_answer_count)
      }

      env {
        name  = "AZURE_SEARCH_QUERY_LANGUAGE"
        value = var.azure_search_query_language
      }

      # Agent Configuration
      env {
        name  = "AGENT_TEMPERATURE"
        value = tostring(var.agent_temperature)
      }

      env {
        name  = "AGENT_MAX_TOKENS"
        value = tostring(var.agent_max_tokens)
      }

      # Azure Document Intelligence Configuration
      dynamic "env" {
        for_each = var.azure_document_intelligence_endpoint != "" ? [var.azure_document_intelligence_endpoint] : []
        content {
          name  = "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
          value = env.value
        }
      }

      env {
        name        = "AZURE_DOCUMENT_INTELLIGENCE_KEY"
        secret_name = "azure-document-intelligence-key"
      }

      # Azure Storage Configuration
      dynamic "env" {
        for_each = var.azure_storage_account_name != "" ? [var.azure_storage_account_name] : []
        content {
          name  = "AZURE_STORAGE_ACCOUNT_NAME"
          value = env.value
        }
      }

      env {
        name        = "AZURE_STORAGE_ACCOUNT_KEY"
        secret_name = "azure-storage-account-key"
      }

      dynamic "env" {
        for_each = var.azure_storage_container_name != "" ? [var.azure_storage_container_name] : []
        content {
          name  = "AZURE_STORAGE_CONTAINER_NAME"
          value = env.value
        }
      }

      # Azure Blob Storage Configuration
      env {
        name        = "AZURE_BLOBSTORAGE_CONNECTIONSTRING"
        secret_name = "azure-blobstorage-connectionstring"
      }

      dynamic "env" {
        for_each = var.azure_blobstorage_container != "" ? [var.azure_blobstorage_container] : []
        content {
          name  = "AZURE_BLOBSTORAGE_CONTAINER"
          value = env.value
        }
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

      env {
        name = "CORS_ALLOW_ORIGINS"
        value = tostring(var.cors_allow_origins)
      }
      # Inject additional conversation-specific env vars from a map
      dynamic "env" {
        for_each = var.conversation_env
        content {
          name  = env.key
          value = env.value
        }
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

      # Cosmos DB Configuration (only set when value provided)
      dynamic "env" {
        for_each = var.cosmosdb_endpoint != "" ? [var.cosmosdb_endpoint] : []
        content {
          name  = "COSMOS_DB_ENDPOINT"
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.cosmosdb_db_name != "" ? [var.cosmosdb_db_name] : []
        content {
          name  = "COSMOS_DB_DATABASE_NAME"
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.cosmosdb_container_name != "" ? [var.cosmosdb_container_name] : []
        content {
          name  = "COSMOS_DB_CONTAINER_NAME"
          value = env.value
        }
      }

      # Azure OpenAI Configuration
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-api-key"
      }

      dynamic "env" {
        for_each = var.azure_openai_endpoint != "" ? [var.azure_openai_endpoint] : []
        content {
          name  = "AZURE_OPENAI_ENDPOINT"
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.azure_openai_api_version != "" ? [var.azure_openai_api_version] : []
        content {
          name  = "AZURE_OPENAI_API_VERSION"
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME != "" ? [var.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME] : []
        content {
          name  = "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
          value = env.value
        }
      }

      # Azure Search Configuration
      dynamic "env" {
        for_each = var.azure_search_endpoint != "" ? [var.azure_search_endpoint] : []
        content {
          name  = "AZURE_SEARCH_ENDPOINT"
          value = env.value
        }
      }

      env {
        name        = "AZURE_SEARCH_API_KEY"
        secret_name = "azure-search-api-key"
      }

      dynamic "env" {
        for_each = var.azure_search_index_name != "" ? [var.azure_search_index_name] : []
        content {
          name  = "AZURE_SEARCH_INDEX_NAME"
          value = env.value
        }
      }

      env {
        name  = "AZURE_SEARCH_TOP"
        value = tostring(var.azure_search_top)
      }

      env {
        name  = "AZURE_SEARCH_TRIM_LENGTH"
        value = tostring(var.azure_search_trim_length)
      }

      env {
        name  = "AZURE_SEARCH_ENABLE_TRIMMING"
        value = tostring(var.azure_search_enable_trimming)
      }

      env {
        name  = "AZURE_SEARCH_INCLUDE_TOTAL_COUNT"
        value = tostring(var.azure_search_include_total_count)
      }

      env {
        name  = "AZURE_SEARCH_QUERY_TYPE"
        value = var.azure_search_query_type
      }

      env {
        name  = "AZURE_SEARCH_SEMANTIC_CONFIGURATION"
        value = var.azure_search_semantic_configuration
      }

      env {
        name  = "AZURE_SEARCH_QUERY_CAPTION"
        value = var.azure_search_query_caption
      }

      env {
        name  = "AZURE_SEARCH_QUERY_ANSWER"
        value = var.azure_search_query_answer
      }

      env {
        name  = "AZURE_SEARCH_QUERY_ANSWER_COUNT"
        value = tostring(var.azure_search_query_answer_count)
      }

      env {
        name  = "AZURE_SEARCH_QUERY_LANGUAGE"
        value = var.azure_search_query_language
      }

      # Agent Configuration
      env {
        name  = "AGENT_TEMPERATURE"
        value = tostring(var.agent_temperature)
      }

      env {
        name  = "AGENT_MAX_TOKENS"
        value = tostring(var.agent_max_tokens)
      }

      # Azure Document Intelligence Configuration
      dynamic "env" {
        for_each = var.azure_document_intelligence_endpoint != "" ? [var.azure_document_intelligence_endpoint] : []
        content {
          name  = "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
          value = env.value
        }
      }

      env {
        name        = "AZURE_DOCUMENT_INTELLIGENCE_KEY"
        secret_name = "azure-document-intelligence-key"
      }

      # Azure Storage Configuration
      dynamic "env" {
        for_each = var.azure_storage_account_name != "" ? [var.azure_storage_account_name] : []
        content {
          name  = "AZURE_STORAGE_ACCOUNT_NAME"
          value = env.value
        }
      }

      env {
        name        = "AZURE_STORAGE_ACCOUNT_KEY"
        secret_name = "azure-storage-account-key"
      }

      dynamic "env" {
        for_each = var.azure_storage_container_name != "" ? [var.azure_storage_container_name] : []
        content {
          name  = "AZURE_STORAGE_CONTAINER_NAME"
          value = env.value
        }
      }

      # Azure Blob Storage Configuration
      env {
        name        = "AZURE_BLOBSTORAGE_CONNECTIONSTRING"
        secret_name = "azure-blobstorage-connectionstring"
      }

      dynamic "env" {
        for_each = var.azure_blobstorage_container != "" ? [var.azure_blobstorage_container] : []
        content {
          name  = "AZURE_BLOBSTORAGE_CONTAINER"
          value = env.value
        }
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

      env {
        name = "CORS_ALLOW_ORIGINS"
        value = tostring(var.cors_allow_origins)
      }
      # Inject additional formsupport-specific env vars from a map
      dynamic "env" {
        for_each = var.formsupport_env
        content {
          name  = env.key
          value = env.value
        }
      }
    }
    /*
    # API Backend Container - Public-facing WebSocket gateway to orchestrator
    container {
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
        value = "ws://localhost:${var.orchestrator_agent_port}/ws"
      }

      env {
        name  = "LOG_LEVEL"
        value = var.log_level
      }

      env {
        name        = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        secret_name = "appinsights-connection-string"
      }

      env {
        name        = "APPINSIGHTS_INSTRUMENTATIONKEY"
        secret_name = "appinsights-instrumentation-key"
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
    */

    # HTTP scaling rule - scale based on concurrent requests
    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = "20"
    }
  }

  ingress {
    external_enabled           = true                        # Must be true for Front Door to reach the public orchestrator endpoint
    target_port                = var.orchestrator_agent_port # Orchestrator Agent is the public-facing ACA endpoint
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

  enabled                        = true
  host_name                      = local.backend_fqdn
  http_port                      = 8002
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
  count                         = var.enable_front_door ? 1 : 0
  name                          = "${var.repo_name}-${var.app_env}-api-fd"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.api_fd_endpoint[0].id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.api_origin_group[0].id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.api_container_app_origin[0].id]

  supported_protocols    = ["Http", "Https"]
  patterns_to_match      = ["/*"]
  forwarding_protocol    = "HttpsOnly"
  link_to_default_domain = true
  https_redirect_enabled = true
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
