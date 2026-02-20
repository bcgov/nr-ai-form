terraform {
  source = "${get_parent_terragrunt_dir()}/../infra"
}

locals {
  stack_prefix             = get_env("stack_prefix")
  conversation_agent_image = get_env("conversation_agent_image")
  formsupport_agent_image  = get_env("formsupport_agent_image")
  orchestrator_agent_image = get_env("orchestrator_agent_image")
  vnet_resource_group_name = get_env("vnet_resource_group_name") # Resource group where the VNet exists.
  vnet_name                = get_env("vnet_name")                # Name of the existing VNet.
  target_env               = get_env("target_env")
  app_env                  = get_env("app_env") # Application environment (dev, test, prod).
  deployment_type          = get_env("deployment_type", "app_service") # Deployment type (app_service or container_apps)
  azure_subscription_id    = get_env("azure_subscription_id")
  azure_tenant_id          = get_env("azure_tenant_id")
  azure_client_id          = get_env("azure_client_id")      # Azure service principal client ID.
  storage_account_name     = get_env("storage_account_name") # Created by initial setup script.
  vnet_address_space       = get_env("vnet_address_space")   # Address space for the VNet.
  statefile_key            = "${local.stack_prefix}/${local.app_env}/terraform.tfstate"
  container_name           = "tfstate"
  
  # Azure OpenAI Configuration
  azure_openai_api_key         = get_env("AZURE_OPENAI_API_KEY")
  azure_openai_endpoint        = get_env("AZURE_OPENAI_ENDPOINT")
  azure_openai_api_version     = get_env("AZURE_OPENAI_API_VERSION", "2024-10-21")
  AZURE_OPENAI_CHAT_DEPLOYMENT_NAME = get_env("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
  
  # Azure Search Configuration
  azure_search_endpoint   = get_env("AZURE_SEARCH_ENDPOINT")
  AZURE_SEARCH_API_KEY        = get_env("AZURE_SEARCH_API_KEY")
  azure_search_index_name = get_env("AZURE_SEARCH_INDEX_NAME")
  
  # Azure Document Intelligence Configuration
  azure_document_intelligence_endpoint = get_env("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
  azure_document_intelligence_key      = get_env("AZURE_DOCUMENT_INTELLIGENCE_KEY")
  
  # Azure Storage Configuration
  azure_storage_account_name   = get_env("AZURE_STORAGE_ACCOUNT_NAME")
  azure_storage_account_key    = get_env("AZURE_STORAGE_ACCOUNT_KEY")
  azure_storage_container_name = get_env("AZURE_STORAGE_CONTAINER_NAME")

  # Azure Blob Storage Configuration
  azure_blobstorage_connectionstring = get_env("AZURE_BLOBSTORAGE_CONNECTIONSTRING")
  azure_blobstorage_container         = get_env("AZURE_BLOBSTORAGE_CONTAINER")
  
  # Container Registry Configuration
  container_registry_url      = get_env("CONTAINER_REGISTRY_URL", "https://ghcr.io")
  container_registry_username = get_env("CONTAINER_REGISTRY_USERNAME", "")
  container_registry_password = get_env("CONTAINER_REGISTRY_PASSWORD", "")
  
  # Agent Port Configuration
  orchestrator_agent_port  = get_env("ORCHESTRATOR_AGENT_PORT", "8002")
  conversation_agent_port  = get_env("CONVERSATION_AGENT_PORT", "8000")
  formsupport_agent_port   = get_env("FORMSUPPORT_AGENT_PORT", "8001")
}

# Remote Azure Storage backend for Terraform
generate "remote_state" {
  path      = "backend.tf"
  if_exists = "overwrite"
  contents  = <<EOF
terraform {
  backend "azurerm" {
    resource_group_name  = "${local.vnet_resource_group_name}"
    storage_account_name = "${local.storage_account_name}"
    container_name       = "${local.container_name}"
    key                  = "${local.statefile_key}"
    subscription_id      = "${local.azure_subscription_id}"
    tenant_id            = "${local.azure_tenant_id}"
    client_id            = "${local.azure_client_id}"
    use_oidc             = true
  }
}
EOF
}

generate "tfvars" {
  path              = "terragrunt.auto.tfvars"
  if_exists         = "overwrite"
  disable_signature = true
  contents          = <<-EOF
resource_group_name        = "${get_env("repo_name")}-${local.app_env}"
app_name                  = "${local.stack_prefix}-${local.app_env}"
app_env                   = "${local.app_env}"
deployment_type           = "${local.deployment_type}"
subscription_id           = "${local.azure_subscription_id}"
tenant_id                 = "${local.azure_tenant_id}"
client_id                 = "${local.azure_client_id}"
vnet_name                 = "${local.vnet_name}"
vnet_resource_group_name  = "${local.vnet_resource_group_name}"
api_image                 = "${local.conversation_agent_image}"  # For Container Apps compatibility
conversation_agent_image  = "${local.conversation_agent_image}"
formsupport_agent_image   = "${local.formsupport_agent_image}"
orchestrator_agent_image  = "${local.orchestrator_agent_image}"
vnet_address_space        = "${local.vnet_address_space}"
repo_name                 = "${get_env("repo_name")}"

# Azure OpenAI Configuration
azure_openai_api_key         = "${local.azure_openai_api_key}"
azure_openai_endpoint        = "${local.azure_openai_endpoint}"
azure_openai_api_version     = "${local.azure_openai_api_version}"
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME = "${local.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME}"

# Azure Search Configuration
azure_search_endpoint   = "${local.azure_search_endpoint}"
AZURE_SEARCH_API_KEY        = "${local.AZURE_SEARCH_API_KEY}"
azure_search_index_name = "${local.azure_search_index_name}"

# Azure Document Intelligence Configuration
azure_document_intelligence_endpoint = "${local.azure_document_intelligence_endpoint}"
azure_document_intelligence_key      = "${local.azure_document_intelligence_key}"

# Azure Storage Configuration
azure_storage_account_name   = "${local.azure_storage_account_name}"
azure_storage_account_key    = "${local.azure_storage_account_key}"
azure_storage_container_name = "${local.azure_storage_container_name}"

# Azure Blob Storage Configuration
azure_blobstorage_connectionstring = "${local.azure_blobstorage_connectionstring}"
azure_blobstorage_container         = "${local.azure_blobstorage_container}"

# Container Registry Configuration
container_registry_url      = "${local.container_registry_url}"
container_registry_username = "${local.container_registry_username}"
container_registry_password = "${local.container_registry_password}"

# Agent Port Configuration
orchestrator_agent_port = "${local.orchestrator_agent_port}"
conversation_agent_port = "${local.conversation_agent_port}"
formsupport_agent_port  = "${local.formsupport_agent_port}"

common_tags = {
  "Environment" = "${local.target_env}"
  "AppEnv"      = "${local.app_env}"
  "AppName"     = "${local.stack_prefix}-${local.app_env}"
  "RepoName"    = "${get_env("repo_name")}"
  "ManagedBy"   = "Terraform"
}
EOF
}
