# Storage account names: 3-24 chars, lowercase letters and numbers only, globally unique.
locals {
  storage_account_name = substr("${replace(lower(var.app_name), "/[^a-z0-9]/", "")}st", 0, 24)
}

resource "azurerm_storage_account" "main" {
  name                            = local.storage_account_name
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_tier                    = "Standard"
  account_kind                    = "StorageV2"
  account_replication_type        = var.account_replication_type
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  allow_nested_items_to_be_public = false
  public_network_access_enabled   = var.public_network_access_enabled
  shared_access_key_enabled       = true # agents read blobs via AZURE_BLOBSTORAGE_CONNECTIONSTRING

  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = var.blob_soft_delete_retention_days
    }
    container_delete_retention_policy {
      days = var.blob_soft_delete_retention_days
    }
  }

  tags = var.common_tags
  lifecycle {
    ignore_changes  = [tags]
    prevent_destroy = true
  }
}

# Created through the ARM control plane (storage_account_id), so it works with public network access disabled.
resource "azurerm_storage_container" "main" {
  name                  = var.container_name
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_monitor_diagnostic_setting" "storage_blob_diagnostics" {
  name                       = "${var.app_name}-storage-blob-diagnostics"
  target_resource_id         = "${azurerm_storage_account.main.id}/blobServices/default"
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "StorageRead"
  }
  enabled_log {
    category = "StorageWrite"
  }
  enabled_log {
    category = "StorageDelete"
  }
}

resource "azurerm_private_endpoint" "storage_blob_private_endpoint" {
  name                = "${var.app_name}-storage-blob-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id
  private_service_connection {
    name                           = "${azurerm_storage_account.main.name}_blob_privateserviceconnection"
    private_connection_resource_id = azurerm_storage_account.main.id
    is_manual_connection           = false
    subresource_names              = ["blob"]
  }
  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags, private_dns_zone_group]
  }
}
