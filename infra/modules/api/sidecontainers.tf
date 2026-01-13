# Sidecar Container Deployment for App Service
#
# CURRENT DEPLOYMENT STRATEGY:
# 1. Orchestrator Agent deployed as main container via Terraform (linux_fx_version)
# 2. Conversation and Form Support agents deployed as sidecars via Azure CLI
#
# WHY CLI-BASED APPROACH:
# - Terraform azurerm provider ~> 4.3 does not support azurerm_web_app_sitecontainer resources
# - These resources require provider >= 4.5.0
# - Using Azure CLI allows immediate deployment while maintaining IaC compatibility
#
# SIDECAR DEPLOYMENT INSTRUCTIONS:
# Execute these commands after the App Service is created and Orchestrator Agent is running
#
# ============================================================================
# DEPLOY CONVERSATION AGENT SIDECAR
# ============================================================================
#
# az webapp sitecontainers create \
#   --name "${APP_NAME}" \
#   --resource-group "${RESOURCE_GROUP}" \
#   --container-name "conversation-agent" \
#   --image "${CONVERSATION_AGENT_IMAGE}" \
#   --target-port 8000 \
#   --cpu 1.0 \
#   --memory 2.0
#
# ============================================================================
# DEPLOY FORM SUPPORT AGENT SIDECAR
# ============================================================================
#
# az webapp sitecontainers create \
#   --name "${APP_NAME}" \
#   --resource-group "${RESOURCE_GROUP}" \
#   --container-name "formsupport-agent" \
#   --image "${FORMSUPPORT_AGENT_IMAGE}" \
#   --target-port 8001 \
#   --cpu 1.0 \
#   --memory 2.0
#
# ============================================================================
# VERIFY SIDECARS ARE RUNNING
# ============================================================================
#
# az webapp sitecontainers list \
#   --name "${APP_NAME}" \
#   --resource-group "${RESOURCE_GROUP}"
#
# ============================================================================
# TERRAFORM MIGRATION (Future - when provider >= 4.5.0)
# ============================================================================
#
# When Azure provider is upgraded to >= 4.5.0, uncomment the resources below
# and remove the Azure CLI deployment steps above.
#
# # Main Container: Orchestrator Agent (already deployed via linux_fx_version)
# # This resource would transition the main container management to Terraform
#
# # Sidecar: Conversation Agent
# resource "azurerm_web_app_sitecontainer" "conversation_agent" {
#   web_app_id      = azurerm_linux_web_app.api.id
#   name            = "conversation-agent"
#   image           = var.conversation_agent_image
#   is_main         = false
#   target_port     = var.conversation_agent_port
#   cpu             = "1.0"
#   memory          = "2.0"
#   depends_on_main = true
#
#   environment_variables = [
#     {
#       name  = "PORT"
#       value = var.conversation_agent_port
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
#   ]
# }
#
# # Sidecar: Form Support Agent
# resource "azurerm_web_app_sitecontainer" "formsupport_agent" {
#   web_app_id      = azurerm_linux_web_app.api.id
#   name            = "formsupport-agent"
#   image           = var.formsupport_agent_image
#   is_main         = false
#   target_port     = var.formsupport_agent_port
#   cpu             = "1.0"
#   memory          = "2.0"
#   depends_on_main = true
#
#   environment_variables = [
#     {
#       name  = "PORT"
#       value = var.formsupport_agent_port
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
#   ]
# }
