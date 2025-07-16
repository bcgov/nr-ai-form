resource "azurerm_servicebus_namespace" "servicebus_namespace" {
  name                          = "${local.abbrs.serviceBusNamespaces}${random_id.random_deployment_suffix.hex}"
  location                      = data.azurerm_resource_group.rg.location
  resource_group_name           = data.azurerm_resource_group.rg.name
  sku                           = "Premium"
  capacity                      = 1
  premium_messaging_partitions  = 1
  local_auth_enabled            = false
  public_network_access_enabled = false

  identity {
    type = "SystemAssigned"
  }
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_servicebus_queue" "servicebus_queue" {
  name         = "queue"
  namespace_id = azurerm_servicebus_namespace.servicebus_namespace.id
}

resource "azurerm_private_endpoint" "servicebus_private_endpoint" {
  name                = "${local.abbrs.privateEndpoint}${local.abbrs.serviceBusNamespaces}${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  subnet_id           = azapi_resource.privateEndpoint_subnet.id
  private_service_connection {
    name                           = "servicebus_privateserviceconnection"
    private_connection_resource_id = azurerm_servicebus_namespace.servicebus_namespace.id
    is_manual_connection           = false
    subresource_names              = ["namespace"]
  }
    lifecycle {
    ignore_changes = [tags, private_dns_zone_group]
  }
}
