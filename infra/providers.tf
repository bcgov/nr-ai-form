terraform {
  required_version = ">= 1.12"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.3"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "~> 2.5"
    }
  }
}
provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
    resource_group {
      #TODO: set to true later, Allow deletion of resource groups with resources, since we are in exploration, 
      prevent_deletion_if_contains_resources = false
    }
  }
  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
  use_oidc        = var.use_oidc
  client_id       = var.client_id
}