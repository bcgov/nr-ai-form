terraform {
  required_version = ">= 1.9.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "4.35.0"
    }
    azapi = {
      source = "Azure/azapi"
      version = "2.3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~>3.0"
    }
  }
}
provider "azurerm" {
  features {}
  # subscription_id will be read from ARM_SUBSCRIPTION_ID environment variable
  # This is automatically set by the GitHub Actions workflow
}
