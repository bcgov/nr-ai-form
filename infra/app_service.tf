# Create the Linux App Service  
resource "azurerm_service_plan" "app_service_plan" {
  name                = "${local.abbrs.webServerFarms}${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  os_type             = "Linux"
  sku_name            = var.app_service_plan_sku
}

# Create the web app, pass in the App Service Plan ID
resource "azurerm_linux_web_app" "app_service" {
  name                = "${local.abbrs.webSitesAppService}${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  service_plan_id     = azurerm_service_plan.app_service_plan.id
  depends_on          = [azurerm_service_plan.app_service_plan]
  https_only          = true

  # Enable system-assigned managed identity
  identity {
    type = "SystemAssigned"
  }

  site_config {
    minimum_tls_version    = "1.2" # Changed from 1.3 for API Management compatibility
    use_32_bit_worker      = false
    vnet_route_all_enabled = true
    ftps_state             = "FtpsOnly"

    application_stack {
      docker_image_name        = var.container_image_name
      docker_registry_url      = var.container_registry_url
      docker_registry_username = var.container_registry_username
      docker_registry_password = var.container_registry_password
    }
  }

  public_network_access_enabled = false
  virtual_network_subnet_id     = azapi_resource.app_service_subnet.id

  app_settings = {
    COSMOS_DB_ENDPOINT       = azurerm_cosmosdb_account.cosmosdb_sql.endpoint
    COSMOS_DB_DATABASE_NAME  = azurerm_cosmosdb_sql_database.cosmosdb_sql_db.name
    COSMOS_DB_CONTAINER_NAME = azurerm_cosmosdb_sql_container.cosmosdb_sql_db_container.name
  }
}

resource "azurerm_private_endpoint" "app_service_private_endpoint" {
  name                = "${local.abbrs.privateEndpoint}${local.abbrs.webSitesAppService}${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  subnet_id           = azapi_resource.privateEndpoint_subnet.id
  private_service_connection {
    name                           = "${azurerm_linux_web_app.app_service.name}_privateserviceconnection"
    private_connection_resource_id = azurerm_linux_web_app.app_service.id
    is_manual_connection           = false
    subresource_names              = ["sites"]
  }
  lifecycle {
    ignore_changes = [tags, private_dns_zone_group]
  }
}
