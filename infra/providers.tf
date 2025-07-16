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
  subscription_id = "8e303ae8-ce14-4e85-9dc3-9d767a42dec8"
  #subscription_id = "9b6ae7b5-90fb-4b00-96b3-5a10cc0cb0a3"
}
