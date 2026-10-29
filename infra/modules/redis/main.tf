resource "azurerm_managed_redis" "main" {
  name                      = "${var.app_name}-redis"
  resource_group_name       = var.resource_group_name
  location                  = var.location
  sku_name                  = var.sku_name
  high_availability_enabled = var.high_availability_enabled
  public_network_access     = var.public_network_access_enabled ? "Enabled" : "Disabled"

  default_database {
    access_keys_authentication_enabled = true # orchestrator authenticates with REDIS_PASSWORD
    client_protocol                    = "Encrypted"
    # EnterpriseCluster exposes a single endpoint, so the plain (non-cluster-aware)
    # redis.Redis client in utils/redisservice.py works. OSSCluster would need RedisCluster.
    clustering_policy = "EnterpriseCluster"
    eviction_policy   = var.eviction_policy
  }

  tags = var.common_tags
  lifecycle {
    ignore_changes  = [tags]
    prevent_destroy = true
  }
}

resource "azurerm_monitor_diagnostic_setting" "redis_diagnostics" {
  name                       = "${var.app_name}-redis-diagnostics"
  target_resource_id         = azurerm_managed_redis.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_metric {
    category = "AllMetrics"
  }
}

resource "azurerm_private_endpoint" "redis_private_endpoint" {
  name                = "${var.app_name}-redis-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id
  private_service_connection {
    name                           = "${azurerm_managed_redis.main.name}_privateserviceconnection"
    private_connection_resource_id = azurerm_managed_redis.main.id
    is_manual_connection           = false
    subresource_names              = ["redisEnterprise"]
  }
  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags, private_dns_zone_group]
  }
}
