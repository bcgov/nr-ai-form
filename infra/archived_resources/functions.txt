resource "azurerm_linux_function_app" "function_app" {
  name                          = "${local.abbrs.webSitesFunctions}${random_id.random_deployment_suffix.hex}"
  location                      = data.azurerm_resource_group.rg.location
  resource_group_name           = data.azurerm_resource_group.rg.name
  storage_account_name          = azurerm_storage_account.storage_account.name
  storage_uses_managed_identity = true
  service_plan_id               = azurerm_service_plan.app_service_plan.id
  virtual_network_subnet_id     = azapi_resource.functions_subnet.id
  vnet_image_pull_enabled       = true
  https_only                    = true



  identity {
    type = "SystemAssigned"
  }
  functions_extension_version = "~4"
  site_config {
    use_32_bit_worker                       = false
    container_registry_use_managed_identity = true
    vnet_route_all_enabled                  = true
    minimum_tls_version                     = "1.3"


    application_stack {
      docker {
        registry_url = azurerm_container_registry.acr.login_server
        image_name   = "nrpermittingazurepoc"
        image_tag    = "latest"
      }
    }

    application_insights_connection_string = azurerm_application_insights.app_insights.connection_string
    application_insights_key               = azurerm_application_insights.app_insights.instrumentation_key
  }
  app_settings = {
    "ServiceBusConnection__fullyQualifiedNamespace" = azurerm_servicebus_namespace.servicebus_namespace.endpoint
    "ServiceBus_Queue_Name" = azurerm_servicebus_queue.servicebus_queue.name
    "Postgresql_Host" : azurerm_postgresql_flexible_server.postgresql_server.fqdn
    "Postgresql_Port" : "5432"
    "Postgresql_Username" : azurerm_postgresql_flexible_server.postgresql_server.administrator_login
    "Postgresql_Password" : azurerm_postgresql_flexible_server.postgresql_server.administrator_password
    "Postgresql_Database" : azurerm_postgresql_flexible_server_database.postgresql_db.name,
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE" = "false"
  }
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_service_plan" "app_service_plan" {
  name                = "${local.abbrs.webServerFarms}${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  os_type             = "Linux"
  sku_name            = "EP1"
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_storage_account" "storage_account" {
  name                            = "${local.abbrs.storageStorageAccounts}${random_id.random_deployment_suffix.hex}"
  resource_group_name             = data.azurerm_resource_group.rg.name
  location                        = data.azurerm_resource_group.rg.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true
  public_network_access_enabled   = false
  allow_nested_items_to_be_public = false
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_private_endpoint" "storage_blob_private_endpoint" {
  name                = "${local.abbrs.privateEndpoint}blob-${local.abbrs.storageStorageAccounts}${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  subnet_id           = azapi_resource.privateEndpoint_subnet.id
  private_service_connection {
    name                           = "blob_privateserviceconnection"
    private_connection_resource_id = azurerm_storage_account.storage_account.id
    is_manual_connection           = false
    subresource_names              = ["blob"]
  }
  lifecycle {
    ignore_changes = [tags, private_dns_zone_group]
  }
}

resource "azurerm_private_endpoint" "storage_queue_private_endpoint" {
  name                = "${local.abbrs.privateEndpoint}queue-${local.abbrs.storageStorageAccounts}${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  subnet_id           = azapi_resource.privateEndpoint_subnet.id
  private_service_connection {
    name                           = "queue_privateserviceconnection"
    private_connection_resource_id = azurerm_storage_account.storage_account.id
    is_manual_connection           = false
    subresource_names              = ["queue"]
  }
  lifecycle {
    ignore_changes = [tags, private_dns_zone_group]
  }
}

resource "azurerm_private_endpoint" "storage_table_private_endpoint" {
  name                = "${local.abbrs.privateEndpoint}table-${local.abbrs.storageStorageAccounts}${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  subnet_id           = azapi_resource.privateEndpoint_subnet.id
  private_service_connection {
    name                           = "table_privateserviceconnection"
    private_connection_resource_id = azurerm_storage_account.storage_account.id
    is_manual_connection           = false
    subresource_names              = ["table"]
  }
  lifecycle {
    ignore_changes = [tags, private_dns_zone_group]
  }
}
