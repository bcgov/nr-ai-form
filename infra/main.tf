# -------------
# Root Level Terraform Configuration
# -------------
# Create the main resource group for all application resources
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.common_tags
  lifecycle {
    ignore_changes  = [tags]
    prevent_destroy = true
  }
}

# -------------
# Modules based on Dependency
# -------------
module "network" {
  source = "./modules/network"

  app_env                  = var.app_env
  deployment_type          = var.deployment_type
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
  count  = var.enable_front_door ? 1 : 0
  source = "./modules/frontdoor"

  app_name            = var.app_name
  common_tags         = var.common_tags
  frontdoor_sku_name  = var.frontdoor_sku_name
  resource_group_name = azurerm_resource_group.main.name

  depends_on = [azurerm_resource_group.main, module.network]
}

## Cosmos DB module enabled
module "cosmos" {
  source = "./modules/cosmos"

  app_name                   = var.app_name
  common_tags                = var.common_tags
  location                   = var.location
  resource_group_name        = azurerm_resource_group.main.name
  private_endpoint_subnet_id = var.app_env == "dev" ? var.dev_private_endpoint_subnet_id : module.network.private_endpoint_subnet_id
  log_analytics_workspace_id = module.monitoring.log_analytics_workspace_id

  cosmosdb_sql_database_name           = "AgentMemoryDB"
  cosmosdb_sql_database_container_name = "ClientProfiles"

  depends_on = [azurerm_resource_group.main, module.network]
}

# Azure AI Search - opt-in (enabled in prod). When disabled, the endpoint/key come from secrets.
module "search" {
  count  = var.enable_search ? 1 : 0
  source = "./modules/search"

  app_name                      = var.app_name
  common_tags                   = var.common_tags
  location                      = var.location
  resource_group_name           = azurerm_resource_group.main.name
  private_endpoint_subnet_id    = var.app_env == "dev" ? var.dev_private_endpoint_subnet_id : module.network.private_endpoint_subnet_id
  log_analytics_workspace_id    = module.monitoring.log_analytics_workspace_id
  search_sku                    = var.search_sku
  semantic_search_sku           = var.search_semantic_sku
  replica_count                 = var.search_replica_count
  partition_count               = var.search_partition_count
  public_network_access_enabled = var.search_public_network_access_enabled

  depends_on = [azurerm_resource_group.main, module.network]
}

# Storage Account (form definitions + prompt templates) - opt-in (enabled in prod).
# When disabled, the connection string / container come from secrets.
module "storage" {
  count  = var.enable_storage ? 1 : 0
  source = "./modules/storage"

  app_name                        = var.app_name
  common_tags                     = var.common_tags
  location                        = var.location
  resource_group_name             = azurerm_resource_group.main.name
  private_endpoint_subnet_id      = var.app_env == "dev" ? var.dev_private_endpoint_subnet_id : module.network.private_endpoint_subnet_id
  log_analytics_workspace_id      = module.monitoring.log_analytics_workspace_id
  container_name                  = var.azure_blobstorage_container != "" ? var.azure_blobstorage_container : var.storage_container_name
  account_replication_type        = var.storage_replication_type
  blob_soft_delete_retention_days = var.storage_blob_soft_delete_retention_days
  public_network_access_enabled   = var.storage_public_network_access_enabled

  depends_on = [azurerm_resource_group.main, module.network]
}

# Azure Managed Redis (thread/session state) - opt-in (enabled in prod).
# When disabled, the host / password come from secrets.
module "redis" {
  count  = var.enable_redis ? 1 : 0
  source = "./modules/redis"

  app_name                      = var.app_name
  common_tags                   = var.common_tags
  location                      = var.location
  resource_group_name           = azurerm_resource_group.main.name
  private_endpoint_subnet_id    = var.app_env == "dev" ? var.dev_private_endpoint_subnet_id : module.network.private_endpoint_subnet_id
  log_analytics_workspace_id    = module.monitoring.log_analytics_workspace_id
  sku_name                      = var.redis_sku_name
  high_availability_enabled     = var.redis_high_availability_enabled
  public_network_access_enabled = var.redis_public_network_access_enabled

  depends_on = [azurerm_resource_group.main, module.network]
}

locals {
  # Prefer Terraform-managed Search/Storage/Redis when enabled, otherwise fall back to the values passed in as secrets.
  azure_search_endpoint = var.enable_search ? module.search[0].search_endpoint : var.azure_search_endpoint
  azure_search_api_key  = var.enable_search ? module.search[0].search_primary_key : var.AZURE_SEARCH_API_KEY

  azure_storage_account_name         = var.enable_storage ? module.storage[0].storage_account_name : var.azure_storage_account_name
  azure_storage_account_key          = var.enable_storage ? module.storage[0].storage_account_primary_key : var.azure_storage_account_key
  azure_storage_container_name       = var.enable_storage ? module.storage[0].storage_container_name : var.azure_storage_container_name
  azure_blobstorage_connectionstring = var.enable_storage ? module.storage[0].storage_blob_connection_string : var.azure_blobstorage_connectionstring
  azure_blobstorage_container        = var.enable_storage ? module.storage[0].storage_container_name : var.azure_blobstorage_container

  # Managed Redis is TLS-only, so redis_ssl is forced to true when Terraform provisions it.
  redis_host     = var.enable_redis ? module.redis[0].redis_hostname : var.redis_host
  redis_port     = var.enable_redis ? module.redis[0].redis_port : var.redis_port
  redis_password = var.enable_redis ? module.redis[0].redis_primary_access_key : var.redis_password
  redis_ssl      = var.enable_redis ? true : var.redis_ssl
}

# Container Apps Deployment (only deployment type supported)
module "container_apps" {
  source = "./modules/container-apps"

  app_name    = var.app_name
  app_env     = var.app_env
  repo_name   = var.repo_name
  branch_slug = var.branch_slug

  # Agent Images
  orchestrator_agent_image = var.orchestrator_agent_image
  conversation_agent_image = var.conversation_agent_image
  formsupport_agent_image  = var.formsupport_agent_image
  api_backend_image        = var.api_backend_image
  backend_image = var.conversation_agent_image # Fallback for compatibility

  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  common_tags         = var.common_tags

  # Networking - Container Apps requires dedicated subnet (cannot be shared)
  # Dev: Uses dev_container_apps_subnet_id (must be manually created/provided)
  # Test/Prod: Uses container_apps_subnet created by network module
  private_endpoint_subnet_id = var.app_env == "dev" ? var.dev_private_endpoint_subnet_id : module.network.private_endpoint_subnet_id
  container_apps_subnet_id   = var.app_env == "dev" ? var.dev_container_apps_subnet_id : module.network.container_apps_subnet_id

  # Container Configuration
  container_cpu                  = var.container_cpu
  container_memory               = var.container_memory
  min_replicas                   = var.min_replicas
  max_replicas                   = var.max_replicas
  internal_load_balancer_enabled = false # Must be false for Front Door to reach the Container App via public HTTPS

  # Agent Ports
  orchestrator_agent_port = var.orchestrator_agent_port
  conversation_agent_port = var.conversation_agent_port
  formsupport_agent_port  = var.formsupport_agent_port
  container_registry_url  = var.container_registry_url

  # CosmosDB
  # Original CosmosDB inputs
    cosmosdb_endpoint       = module.cosmos.cosmosdb_endpoint
    cosmosdb_db_name        = module.cosmos.cosmosdb_sql_database_name
    cosmosdb_container_name = module.cosmos.cosmosdb_sql_database_container_name
  # CosmosDB (disabled for now)
  #cosmosdb_endpoint       = ""
  #cosmosdb_db_name        = ""
  #cosmosdb_container_name = ""

  # Monitoring
  log_analytics_workspace_id      = module.monitoring.log_analytics_workspace_id
  appinsights_instrumentation_key = module.monitoring.appinsights_instrumentation_key
  appinsights_connection_string   = module.monitoring.appinsights_connection_string

  # Front Door
  enable_front_door                = var.enable_front_door
  api_frontdoor_id                 = var.enable_front_door ? module.frontdoor[0].frontdoor_id : ""
  api_frontdoor_resource_guid      = var.enable_front_door ? module.frontdoor[0].frontdoor_resource_guid : ""
  api_frontdoor_firewall_policy_id = var.enable_front_door ? module.frontdoor[0].firewall_policy_id : ""

  # Azure OpenAI
  azure_openai_api_key              = var.azure_openai_api_key
  azure_openai_endpoint             = var.azure_openai_endpoint
  azure_openai_api_version          = var.azure_openai_api_version
  AZURE_OPENAI_CHAT_DEPLOYMENT_NAME = var.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME

  # Azure Search
  azure_search_endpoint        = local.azure_search_endpoint
  AZURE_SEARCH_API_KEY         = local.azure_search_api_key
  azure_search_index_name      = var.azure_search_index_name
  azure_search_top             = var.azure_search_top
  azure_search_trim_length     = var.azure_search_trim_length
  azure_search_enable_trimming = var.azure_search_enable_trimming

  # Extended Azure Search Configuration
  azure_search_include_total_count    = var.azure_search_include_total_count
  azure_search_query_type             = var.azure_search_query_type
  azure_search_semantic_configuration = var.azure_search_semantic_configuration
  azure_search_query_caption          = var.azure_search_query_caption
  azure_search_query_answer           = var.azure_search_query_answer
  azure_search_query_answer_count     = var.azure_search_query_answer_count
  azure_search_query_language         = var.azure_search_query_language

  # LLM Agent Configuration
  agent_temperature = var.agent_temperature
  agent_max_tokens  = var.agent_max_tokens

  # Azure Document Intelligence
  azure_document_intelligence_endpoint = var.azure_document_intelligence_endpoint
  azure_document_intelligence_key      = var.azure_document_intelligence_key

  # Azure Storage
  azure_storage_account_name   = local.azure_storage_account_name
  azure_storage_account_key    = local.azure_storage_account_key
  azure_storage_container_name = local.azure_storage_container_name

  # Azure Blob Storage
  azure_blobstorage_connectionstring = local.azure_blobstorage_connectionstring
  azure_blobstorage_container        = local.azure_blobstorage_container

  # Azure Cosmos DB Configuration
  azure_cosmos_db_endpoint      = var.azure_cosmos_db_endpoint
  azure_cosmos_db_key           = var.azure_cosmos_db_key
  azure_cosmos_db_database_name = var.azure_cosmos_db_database_name

  # Tenant Profile Configuration
  tenant_profile_fresh_ttl_seconds         = var.tenant_profile_fresh_ttl_seconds
  tenant_profile_stale_ttl_seconds         = var.tenant_profile_stale_ttl_seconds
  tenant_profile_lookup_timeout_seconds    = var.tenant_profile_lookup_timeout_seconds

  # Cache Configuration
  orchestrator_prompt_cache_ttl_seconds    = var.orchestrator_prompt_cache_ttl_seconds
  conversation_prompt_cache_ttl_seconds    = var.conversation_prompt_cache_ttl_seconds
  form_support_agent_cache_ttl_seconds     = var.form_support_agent_cache_ttl_seconds
  form_support_prompt_cache_ttl_seconds    = var.form_support_prompt_cache_ttl_seconds
  form_support_asset_cache_ttl_seconds     = var.form_support_asset_cache_ttl_seconds

  # Redis
  redis_host     = local.redis_host
  redis_port     = local.redis_port
  redis_password = local.redis_password
  redis_ssl      = local.redis_ssl
  redis_ttl_days = var.redis_ttl_days

  cors_allow_origins = var.cors_allow_origins
  
  # Original dependency included Cosmos module (commented out)
  depends_on = [module.network, module.cosmos, module.monitoring]
  #  depends_on = [module.network, module.monitoring]
}




# Assign the Container App's managed identity to the Cosmos DB SQL Database with Data Contributor role
resource "azurerm_cosmosdb_sql_role_assignment" "cosmosdb_role_assignment_container_app_data_contributor" {
  resource_group_name = var.resource_group_name
  account_name        = module.cosmos.account_name
  role_definition_id  = "${module.cosmos.account_id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = module.container_apps.backend_managed_identity_principal_id
  scope               = module.cosmos.account_id
}
