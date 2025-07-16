resource "random_password" "postgresql_admin_password" {
  length           = 16
  special          = false
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "azurerm_postgresql_flexible_server" "postgresql_server" {
  name                          = "${local.abbrs.dBforPostgreSQLServers}${random_id.random_deployment_suffix.hex}"
  location                      = data.azurerm_resource_group.rg.location
  resource_group_name           = data.azurerm_resource_group.rg.name
  version                       = var.postgresql_server_version
  public_network_access_enabled = false
  zone                          = 1
  administrator_login           = var.postgresql_admin_login
  administrator_password        = random_password.postgresql_admin_password.result

  storage_mb                   = var.postgresql_storage_mb
  storage_tier                 = var.postgresql_storage_tier
  auto_grow_enabled           = var.postgresql_auto_grow_enabled
  backup_retention_days       = var.postgresql_backup_retention_days
  geo_redundant_backup_enabled = var.postgresql_geo_redundant_backup_enabled

  sku_name = var.postgresql_sku_name

  authentication {
    active_directory_auth_enabled = var.postgresql_ad_auth_enabled
    password_auth_enabled         = var.postgresql_password_auth_enabled
  }
    lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_private_endpoint" "postgresql_server_private_endpoint" {
  name                = "${local.abbrs.privateEndpoint}${local.abbrs.dBforPostgreSQLServers}${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  subnet_id           = azapi_resource.privateEndpoint_subnet.id
  
  private_service_connection {
    name                           = "${azurerm_postgresql_flexible_server.postgresql_server.name}_privateserviceconnection"
    private_connection_resource_id = azurerm_postgresql_flexible_server.postgresql_server.id
    is_manual_connection           = false
    subresource_names              = ["postgresqlServer"]
  }
    lifecycle {
    ignore_changes = [tags, private_dns_zone_group]
  }
}

resource "azurerm_postgresql_flexible_server_database" "postgresql_db" {
  name      = "${local.abbrs.dBforPostgreSQLServers}db-${random_id.random_deployment_suffix.hex}"
  server_id = azurerm_postgresql_flexible_server.postgresql_server.id
  collation = "en_US.utf8"
  charset   = "UTF8"
}
