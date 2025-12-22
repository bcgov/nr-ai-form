# -------------
# Root Level Terraform Configuration
# -------------
# Create the main resource group for all application resources
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.common_tags
  lifecycle {
    ignore_changes = [
      tags
    ]
  }
}

# -------------
# Modules based on Dependency
# -------------
module "network" {
  source = "./modules/network"
  
  app_env                  = var.app_env
  common_tags              = var.common_tags
  resource_group_name      = azurerm_resource_group.main.name
  vnet_address_space       = var.vnet_address_space
  vnet_name                = var.vnet_name
  vnet_resource_group_name = var.vnet_resource_group_name

  depends_on = [azurerm_resource_group.main]
}

module "monitoring" {
  source = "./modules/monitoring"

  app_name                     = var.app_name
  common_tags                  = var.common_tags
  location                     = var.location
  log_analytics_retention_days = var.log_analytics_retention_days
  log_analytics_sku            = var.log_analytics_sku
  resource_group_name          = azurerm_resource_group.main.name

  depends_on = [azurerm_resource_group.main, module.network]
}

module "frontdoor" {
  source = "./modules/frontdoor"

  app_name            = var.app_name
  common_tags         = var.common_tags
  frontdoor_sku_name  = var.frontdoor_sku_name
  resource_group_name = azurerm_resource_group.main.name

  depends_on = [azurerm_resource_group.main, module.network]
}

module "cosmos" {
  source = "./modules/cosmos"

  app_name                   = var.app_name
  common_tags                = var.common_tags
  location                   = var.location
  resource_group_name        = azurerm_resource_group.main.name
  private_endpoint_subnet_id = var.app_env == "dev" ? var.dev_private_endpoint_subnet_id  : module.network.private_endpoint_subnet_id
  log_analytics_workspace_id = module.monitoring.log_analytics_workspace_id
  
  depends_on = [azurerm_resource_group.main, module.network]
}

# Conditional deployment: App Service OR Container Apps (never both)
module "api" {
  count  = var.deployment_type == "app_service" ? 1 : 0
  source = "./modules/api"

  app_name            = var.app_name
  app_env             = var.app_env
  repo_name           = var.repo_name
  api_image           = var.api_image
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  common_tags         = var.common_tags

  # Networking
  private_endpoint_subnet_id = var.app_env == "dev" ? var.dev_app_service_subnet_id : module.network.private_endpoint_subnet_id
  app_service_subnet_id      = var.app_env == "dev" ? var.dev_app_service_subnet_id : module.network.app_service_subnet_id

  # App Service
  app_service_sku_name_api = var.app_service_sku_name_api

  # CosmosDB
  cosmosdb_endpoint       = module.cosmos.cosmosdb_endpoint
  cosmosdb_db_name        = module.cosmos.cosmosdb_sql_database_name
  cosmosdb_container_name = module.cosmos.cosmosdb_sql_database_container_name


  # Monitoring
  log_analytics_workspace_id      = module.monitoring.log_analytics_workspace_id
  appinsights_instrumentation_key = module.monitoring.appinsights_instrumentation_key
  appinsights_connection_string   = module.monitoring.appinsights_connection_string

  # Frontdoor
  api_frontdoor_id                 = module.frontdoor.frontdoor_id
  api_frontdoor_resource_guid      = module.frontdoor.frontdoor_resource_guid
  api_frontdoor_firewall_policy_id = module.frontdoor.firewall_policy_id

  # Azure OpenAI
  azure_openai_api_key         = var.azure_openai_api_key
  azure_openai_endpoint        = var.azure_openai_endpoint
  azure_openai_api_version     = var.azure_openai_api_version
  azure_openai_deployment_name = var.azure_openai_deployment_name

  # Azure Search
  azure_search_endpoint   = var.azure_search_endpoint
  azure_search_key        = var.azure_search_key
  azure_search_index_name = var.azure_search_index_name

  # Azure Document Intelligence
  azure_document_intelligence_endpoint = var.azure_document_intelligence_endpoint
  azure_document_intelligence_key      = var.azure_document_intelligence_key

  # Azure Storage
  azure_storage_account_name   = var.azure_storage_account_name
  azure_storage_account_key    = var.azure_storage_account_key
  azure_storage_container_name = var.azure_storage_container_name

  depends_on = [module.frontdoor]
}

module "container_apps" {
  count  = var.deployment_type == "container_apps" ? 1 : 0
  source = "./modules/container-apps"

  app_name            = var.app_name
  app_env             = var.app_env
  repo_name           = var.repo_name
  backend_image       = var.api_image
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  common_tags         = var.common_tags

  # Networking - Container Apps requires dedicated subnet (cannot be shared)
  # Dev: Uses dev_container_apps_subnet_id (must be manually created/provided)
  # Test/Prod: Uses container_apps_subnet created by network module
  private_endpoint_subnet_id = var.app_env == "dev" ? var.dev_private_endpoint_subnet_id : module.network.private_endpoint_subnet_id
  container_apps_subnet_id   = var.app_env == "dev" ? var.dev_container_apps_subnet_id : module.network.container_apps_subnet_id

  # Container Configuration
  container_cpu    = var.container_cpu
  container_memory = var.container_memory
  min_replicas     = var.min_replicas
  max_replicas     = var.max_replicas

  # CosmosDB
  cosmosdb_endpoint       = module.cosmos.cosmosdb_endpoint
  cosmosdb_db_name        = module.cosmos.cosmosdb_sql_database_name
  cosmosdb_container_name = module.cosmos.cosmosdb_sql_database_container_name

  # Monitoring
  log_analytics_workspace_id      = module.monitoring.log_analytics_workspace_id
  appinsights_instrumentation_key = module.monitoring.appinsights_instrumentation_key
  appinsights_connection_string   = module.monitoring.appinsights_connection_string

  # Front Door
  api_frontdoor_id                 = module.frontdoor.frontdoor_id
  api_frontdoor_resource_guid      = module.frontdoor.frontdoor_resource_guid
  api_frontdoor_firewall_policy_id = module.frontdoor.firewall_policy_id

  # Azure OpenAI
  azure_openai_api_key         = var.azure_openai_api_key
  azure_openai_endpoint        = var.azure_openai_endpoint
  azure_openai_api_version     = var.azure_openai_api_version
  azure_openai_deployment_name = var.azure_openai_deployment_name

  # Azure Search
  azure_search_endpoint   = var.azure_search_endpoint
  azure_search_key        = var.azure_search_key
  azure_search_index_name = var.azure_search_index_name

  # Azure Document Intelligence
  azure_document_intelligence_endpoint = var.azure_document_intelligence_endpoint
  azure_document_intelligence_key      = var.azure_document_intelligence_key

  # Azure Storage
  azure_storage_account_name   = var.azure_storage_account_name
  azure_storage_account_key    = var.azure_storage_account_key
  azure_storage_container_name = var.azure_storage_container_name

  depends_on = [module.frontdoor, module.network, module.cosmos, module.monitoring]
}




# due to circular dependency issues this resource is created at root level
// Assign the App Service's managed identity to the Cosmos DB SQL Database with Data Contributor role

resource "azurerm_cosmosdb_sql_role_assignment" "cosmosdb_role_assignment_app_service_data_contributor" {
  count               = var.deployment_type == "app_service" ? 1 : 0
  resource_group_name = var.resource_group_name
  account_name        = module.cosmos.account_name
  role_definition_id  = "${module.cosmos.account_id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = module.api[0].api_managed_identity_principal_id
  scope               = module.cosmos.account_id
}

# Assign the Container App's managed identity to the Cosmos DB SQL Database with Data Contributor role
resource "azurerm_cosmosdb_sql_role_assignment" "cosmosdb_role_assignment_container_app_data_contributor" {
  count               = var.deployment_type == "container_apps" ? 1 : 0
  resource_group_name = var.resource_group_name
  account_name        = module.cosmos.account_name
  role_definition_id  = "${module.cosmos.account_id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = module.container_apps[0].backend_managed_identity_principal_id
  scope               = module.cosmos.account_id
}
