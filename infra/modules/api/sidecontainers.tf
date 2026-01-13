# Sidecar Container Definitions for App Service
# This file defines the Orchestrator Agent as the main container and the
# Conversation and Form Support agents as sidecars

# Main Container: Orchestrator Agent
resource "azurerm_web_app_sitecontainer" "orchestrator_agent" {
  name                 = "orchestrator-agent"
  web_app_id           = azurerm_linux_web_app.api.id
  image                = var.orchestrator_agent_image
  is_main              = true
  target_port          = var.orchestrator_agent_port
  auth_type            = "UserAssigned"
  user_managed_identity_client_id = azurerm_user_assigned_identity.api.client_id

  environment_variables = [
    {
      name  = "PORT"
      value = var.orchestrator_agent_port
    },
    {
      name  = "LOG_LEVEL"
      value = "INFO"
    },
    {
      name  = "CONVERSATION_AGENT_A2A_URL"
      value = "http://localhost:${var.conversation_agent_port}"
    },
    {
      name  = "FORM_SUPPORT_AGENT_A2A_URL"
      value = "http://localhost:${var.formsupport_agent_port}"
    },
    # App Insights
    {
      name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
      value = var.appinsights_connection_string
    },
    {
      name  = "APPINSIGHTS_INSTRUMENTATIONKEY"
      value = var.appinsights_instrumentation_key
    },
    # Cosmos DB
    {
      name  = "COSMOS_DB_ENDPOINT"
      value = var.cosmosdb_endpoint
    },
    {
      name  = "COSMOS_DB_DATABASE_NAME"
      value = var.cosmosdb_db_name
    },
    {
      name  = "COSMOS_DB_CONTAINER_NAME"
      value = var.cosmosdb_container_name
    },
    # Azure OpenAI Configuration
    {
      name  = "AZURE_OPENAI_API_KEY"
      value = var.azure_openai_api_key
    },
    {
      name  = "AZURE_OPENAI_ENDPOINT"
      value = var.azure_openai_endpoint
    },
    {
      name  = "AZURE_OPENAI_API_VERSION"
      value = var.azure_openai_api_version
    },
    {
      name  = "AZURE_OPENAI_DEPLOYMENT_NAME"
      value = var.azure_openai_deployment_name
    },
    # Azure Search Configuration
    {
      name  = "AZURE_SEARCH_ENDPOINT"
      value = var.azure_search_endpoint
    },
    {
      name  = "AZURE_SEARCH_KEY"
      value = var.azure_search_key
    },
    {
      name  = "AZURE_SEARCH_INDEX_NAME"
      value = var.azure_search_index_name
    },
    # Azure Document Intelligence Configuration
    {
      name  = "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
      value = var.azure_document_intelligence_endpoint
    },
    {
      name  = "AZURE_DOCUMENT_INTELLIGENCE_KEY"
      value = var.azure_document_intelligence_key
    },
    # Azure Storage Configuration
    {
      name  = "AZURE_STORAGE_ACCOUNT_NAME"
      value = var.azure_storage_account_name
    },
    {
      name  = "AZURE_STORAGE_ACCOUNT_KEY"
      value = var.azure_storage_account_key
    },
    {
      name  = "AZURE_STORAGE_CONTAINER_NAME"
      value = var.azure_storage_container_name
    }
  ]

  depends_on = [
    azurerm_linux_web_app.api,
    azurerm_user_assigned_identity.api,
    azurerm_role_assignment.api_acr_pull
  ]
}

# Sidecar 1: Conversation Agent
resource "azurerm_web_app_sitecontainer" "conversation_agent" {
  name                 = "conversation-agent"
  web_app_id           = azurerm_linux_web_app.api.id
  image                = var.conversation_agent_image
  is_main              = false
  target_port          = var.conversation_agent_port
  auth_type            = "UserAssigned"
  user_managed_identity_client_id = azurerm_user_assigned_identity.api.client_id

  environment_variables = [
    {
      name  = "PORT"
      value = var.conversation_agent_port
    },
    {
      name  = "LOG_LEVEL"
      value = "INFO"
    },
    # App Insights - inherited from main container but can be overridden
    {
      name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
      value = var.appinsights_connection_string
    },
    {
      name  = "APPINSIGHTS_INSTRUMENTATIONKEY"
      value = var.appinsights_instrumentation_key
    }
  ]

  depends_on = [
    azurerm_linux_web_app.api,
    azurerm_user_assigned_identity.api,
    azurerm_role_assignment.api_acr_pull
  ]
}

# Sidecar 2: Form Support Agent
resource "azurerm_web_app_sitecontainer" "formsupport_agent" {
  name                 = "formsupport-agent"
  web_app_id           = azurerm_linux_web_app.api.id
  image                = var.formsupport_agent_image
  is_main              = false
  target_port          = var.formsupport_agent_port
  auth_type            = "UserAssigned"
  user_managed_identity_client_id = azurerm_user_assigned_identity.api.client_id

  environment_variables = [
    {
      name  = "PORT"
      value = var.formsupport_agent_port
    },
    {
      name  = "LOG_LEVEL"
      value = "INFO"
    },
    # App Insights - inherited from main container but can be overridden
    {
      name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
      value = var.appinsights_connection_string
    },
    {
      name  = "APPINSIGHTS_INSTRUMENTATIONKEY"
      value = var.appinsights_instrumentation_key
    }
  ]

  depends_on = [
    azurerm_linux_web_app.api,
    azurerm_user_assigned_identity.api,
    azurerm_role_assignment.api_acr_pull
  ]
}
