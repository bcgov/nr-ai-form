resource "azurerm_ai_services" "example" {
  name                = "exampleaiservices"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  sku_name            = "S0"
}

resource "azurerm_ai_foundry" "example" {
  name                = "exampleaihub"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  storage_account_id  = azurerm_storage_account.storage_account.id
  key_vault_id        = azurerm_key_vault.example.id

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_ai_foundry_project" "example" {
  name               = "example"
  location           = data.azurerm_resource_group.rg.location
  ai_services_hub_id = azurerm_ai_foundry.example.id
}

resource "azurerm_key_vault" "example" {
  name                = "awtestexamplekv"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  tenant_id           = data.azurerm_subscription.current.tenant_id

  sku_name                 = "standard"
  purge_protection_enabled = true
}