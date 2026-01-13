# Sidecar Container Definitions for App Service
#
# NOTE: Azure App Service sidecars require Azure provider >= 4.5.0 with azurerm_web_app_sitecontainer resources
# Current provider version (~> 4.3) does not support these resource types.
# This file contains commented examples for future migration.
#
# CURRENT IMPLEMENTATION: Docker Compose (see main.tf for configuration)
# Docker Compose multi-container approach works with current provider and provides
# all necessary inter-agent communication via localhost networking.
#
# FOR FUTURE MIGRATION TO NATIVE SIDECARS:
# When upgrading Azure provider to >= 4.5.0, uncomment the resources below
# and remove Docker Compose configuration from main.tf app_settings.
#
# Manual setup (if desired before provider upgrade):
# 1. Enable sidecar mode on the App Service:
#    az webapp config appsettings set \
#      --name <app-name> \
#      --resource-group <resource-group> \
#      --settings DOCKER_ENABLE_CI=true DOCKER_ENABLE_CI_WITH_COMPOSER=true WEBSITES_ENABLE_APP_SERVICE_STORAGE=false
#
# 2. Create Orchestrator Agent (main container):
#    az webapp sitecontainers create \
#      --name <app-name> \
#      --resource-group <resource-group> \
#      --container-name orchestrator-agent \
#      --image <orchestrator-image>:tag \
#      --target-port 8002
#
# 3. Create Conversation Agent Sidecar:
#    az webapp sitecontainers create \
#      --name <app-name> \
#      --resource-group <resource-group> \
#      --container-name conversation-agent \
#      --image <conversation-image>:tag \
#      --target-port 8000
#
# 4. Create Form Support Agent Sidecar:
#    az webapp sitecontainers create \
#      --name <app-name> \
#      --resource-group <resource-group> \
#      --container-name formsupport-agent \
#      --image <formsupport-image>:tag \
#      --target-port 8001
#
# ============================================================================
# TERRAFORM RESOURCES FOR FUTURE USE (Uncomment when provider >= 4.5.0)
# ============================================================================
#
# # Main Container: Orchestrator Agent
# resource "azurerm_web_app_sitecontainer" "orchestrator_agent" {
#   name                 = "orchestrator-agent"
#   web_app_id           = azurerm_linux_web_app.api.id
#   image                = var.orchestrator_agent_image
#   is_main              = true
#   target_port          = var.orchestrator_agent_port
#   auth_type            = "SystemAssigned"
#
#   environment_variables = [
#     {
#       name  = "PORT"
#       value = var.orchestrator_agent_port
#     },
#     {
#       name  = "LOG_LEVEL"
#       value = "INFO"
#     },
#     {
#       name  = "CONVERSATION_AGENT_A2A_URL"
#       value = "http://localhost:${var.conversation_agent_port}"
#     },
#     {
#       name  = "FORM_SUPPORT_AGENT_A2A_URL"
#       value = "http://localhost:${var.formsupport_agent_port}"
#     },
#     {
#       name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
#       value = var.appinsights_connection_string
#     },
#     {
#       name  = "APPINSIGHTS_INSTRUMENTATIONKEY"
#       value = var.appinsights_instrumentation_key
#     },
#     {
#       name  = "COSMOS_DB_ENDPOINT"
#       value = var.cosmosdb_endpoint
#     },
#     {
#       name  = "COSMOS_DB_DATABASE_NAME"
#       value = var.cosmosdb_db_name
#     },
#     {
#       name  = "COSMOS_DB_CONTAINER_NAME"
#       value = var.cosmosdb_container_name
#     },
#     {
#       name  = "AZURE_OPENAI_API_KEY"
#       value = var.azure_openai_api_key
#     },
#     {
#       name  = "AZURE_OPENAI_ENDPOINT"
#       value = var.azure_openai_endpoint
#     },
#     {
#       name  = "AZURE_OPENAI_API_VERSION"
#       value = var.azure_openai_api_version
#     },
#     {
#       name  = "AZURE_OPENAI_DEPLOYMENT_NAME"
#       value = var.azure_openai_deployment_name
#     },
#     {
#       name  = "AZURE_SEARCH_ENDPOINT"
#       value = var.azure_search_endpoint
#     },
#     {
#       name  = "AZURE_SEARCH_KEY"
#       value = var.azure_search_key
#     },
#     {
#       name  = "AZURE_SEARCH_INDEX_NAME"
#       value = var.azure_search_index_name
#     },
#     {
#       name  = "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
#       value = var.azure_document_intelligence_endpoint
#     },
#     {
#       name  = "AZURE_DOCUMENT_INTELLIGENCE_KEY"
#       value = var.azure_document_intelligence_key
#     },
#     {
#       name  = "AZURE_STORAGE_ACCOUNT_NAME"
#       value = var.azure_storage_account_name
#     },
#     {
#       name  = "AZURE_STORAGE_ACCOUNT_KEY"
#       value = var.azure_storage_account_key
#     },
#     {
#       name  = "AZURE_STORAGE_CONTAINER_NAME"
#       value = var.azure_storage_container_name
#     },
#   ]
# }
#
# # Sidecar: Conversation Agent
# resource "azurerm_web_app_sitecontainer" "conversation_agent" {
#   name                = "conversation-agent"
#   web_app_id          = azurerm_linux_web_app.api.id
#   image               = var.conversation_agent_image
#   is_main             = false
#   target_port         = var.conversation_agent_port
#   auth_type           = "SystemAssigned"
#   depends_on_main     = true
#
#   environment_variables = [
#     {
#       name  = "PORT"
#       value = var.conversation_agent_port
#     },
#     {
#       name  = "LOG_LEVEL"
#       value = "INFO"
#     },
#     {
#       name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
#       value = var.appinsights_connection_string
#     },
#     {
#       name  = "APPINSIGHTS_INSTRUMENTATIONKEY"
#       value = var.appinsights_instrumentation_key
#     },
#     {
#       name  = "COSMOS_DB_ENDPOINT"
#       value = var.cosmosdb_endpoint
#     },
#     {
#       name  = "COSMOS_DB_DATABASE_NAME"
#       value = var.cosmosdb_db_name
#     },
#     {
#       name  = "COSMOS_DB_CONTAINER_NAME"
#       value = var.cosmosdb_container_name
#     },
#     {
#       name  = "AZURE_OPENAI_API_KEY"
#       value = var.azure_openai_api_key
#     },
#     {
#       name  = "AZURE_OPENAI_ENDPOINT"
#       value = var.azure_openai_endpoint
#     },
#     {
#       name  = "AZURE_OPENAI_API_VERSION"
#       value = var.azure_openai_api_version
#     },
#     {
#       name  = "AZURE_OPENAI_DEPLOYMENT_NAME"
#       value = var.azure_openai_deployment_name
#     },
#     {
#       name  = "AZURE_SEARCH_ENDPOINT"
#       value = var.azure_search_endpoint
#     },
#     {
#       name  = "AZURE_SEARCH_KEY"
#       value = var.azure_search_key
#     },
#     {
#       name  = "AZURE_SEARCH_INDEX_NAME"
#       value = var.azure_search_index_name
#     },
#     {
#       name  = "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
#       value = var.azure_document_intelligence_endpoint
#     },
#     {
#       name  = "AZURE_DOCUMENT_INTELLIGENCE_KEY"
#       value = var.azure_document_intelligence_key
#     },
#   ]
# }
#
# # Sidecar: Form Support Agent
# resource "azurerm_web_app_sitecontainer" "formsupport_agent" {
#   name                = "formsupport-agent"
#   web_app_id          = azurerm_linux_web_app.api.id
#   image               = var.formsupport_agent_image
#   is_main             = false
#   target_port         = var.formsupport_agent_port
#   auth_type           = "SystemAssigned"
#   depends_on_main     = true
#
#   environment_variables = [
#     {
#       name  = "PORT"
#       value = var.formsupport_agent_port
#     },
#     {
#       name  = "LOG_LEVEL"
#       value = "INFO"
#     },
#     {
#       name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
#       value = var.appinsights_connection_string
#     },
#     {
#       name  = "APPINSIGHTS_INSTRUMENTATIONKEY"
#       value = var.appinsights_instrumentation_key
#     },
#     {
#       name  = "COSMOS_DB_ENDPOINT"
#       value = var.cosmosdb_endpoint
#     },
#     {
#       name  = "COSMOS_DB_DATABASE_NAME"
#       value = var.cosmosdb_db_name
#     },
#     {
#       name  = "COSMOS_DB_CONTAINER_NAME"
#       value = var.cosmosdb_container_name
#     },
#     {
#       name  = "AZURE_OPENAI_API_KEY"
#       value = var.azure_openai_api_key
#     },
#     {
#       name  = "AZURE_OPENAI_ENDPOINT"
#       value = var.azure_openai_endpoint
#     },
#     {
#       name  = "AZURE_OPENAI_API_VERSION"
#       value = var.azure_openai_api_version
#     },
#     {
#       name  = "AZURE_OPENAI_DEPLOYMENT_NAME"
#       value = var.azure_openai_deployment_name
#     },
#     {
#       name  = "AZURE_SEARCH_ENDPOINT"
#       value = var.azure_search_endpoint
#     },
#     {
#       name  = "AZURE_SEARCH_KEY"
#       value = var.azure_search_key
#     },
#     {
#       name  = "AZURE_SEARCH_INDEX_NAME"
#       value = var.azure_search_index_name
#     },
#     {
#       name  = "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
#       value = var.azure_document_intelligence_endpoint
#     },
#     {
#       name  = "AZURE_DOCUMENT_INTELLIGENCE_KEY"
#       value = var.azure_document_intelligence_key
#     },
#   ]
# }
