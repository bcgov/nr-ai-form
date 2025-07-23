terraform {
  source = "../..//infra"
}

locals {
  stack_prefix               = get_env("stack_prefix")
  api_image                  = get_env("api_image")
  vnet_resource_group_name   = get_env("vnet_resource_group_name") # Resource group where the VNet exists.
  vnet_name                  = get_env("vnet_name")                # Name of the existing VNet.
  target_env                 = get_env("target_env")
  app_env                    = get_env("app_env")                  # Application environment (dev, test, prod).
  azure_subscription_id      = get_env("azure_subscription_id")
  azure_tenant_id            = get_env("azure_tenant_id")
  azure_client_id            = get_env("azure_client_id")          # Azure service principal client ID.
  storage_account_name       = get_env("storage_account_name")     # Created by initial setup script.
  vnet_address_space         = get_env("vnet_address_space")       # Address space for the VNet.
  statefile_key              = "${local.stack_prefix}/${local.app_env}/terraform.tfstate"
  container_name             = "tfstate"
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
subscription_id           = "${local.azure_subscription_id}"
tenant_id                 = "${local.azure_tenant_id}"
client_id                 = "${local.azure_client_id}"
vnet_name                 = "${local.vnet_name}"
vnet_resource_group_name  = "${local.vnet_resource_group_name}"
api_image                 = "${local.api_image}"
vnet_address_space        = "${local.vnet_address_space}"

common_tags = {
  "Environment" = "${local.target_env}"
  "AppEnv"      = "${local.app_env}"
  "AppName"     = "${local.stack_prefix}-${local.app_env}"
  "RepoName"    = "${get_env("repo_name")}"
  "ManagedBy"   = "Terraform"
}
EOF
}
