resource "azurerm_cognitive_account" "main" {
  name                          = "${var.app_name}-openai"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  kind                          = "OpenAI"
  sku_name                      = "S0"
  custom_subdomain_name         = "${var.app_name}-openai" # required for private endpoints and Entra ID auth
  public_network_access_enabled = var.public_network_access_enabled
  local_auth_enabled            = var.local_auth_enabled

  identity {
    type = "SystemAssigned"
  }

  tags = var.common_tags
  lifecycle {
    ignore_changes  = [tags]
    prevent_destroy = true
  }
}

# Embedding model used by Azure AI Search (vectorizer / embedding skill) for the knowledge base index.
resource "azurerm_cognitive_deployment" "embedding" {
  name                 = var.embedding_deployment_name
  cognitive_account_id = azurerm_cognitive_account.main.id

  model {
    format  = "OpenAI"
    name    = "text-embedding-3-large"
    version = var.embedding_model_version
  }

  sku {
    name     = var.embedding_sku_name
    capacity = var.embedding_capacity
  }
}

resource "azurerm_monitor_diagnostic_setting" "openai_diagnostics" {
  name                       = "${var.app_name}-openai-diagnostics"
  target_resource_id         = azurerm_cognitive_account.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "Audit"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

# Private endpoint in the VNet so the Container Apps (and indexing jobs) can reach the account.
resource "azurerm_private_endpoint" "openai_private_endpoint" {
  name                = "${var.app_name}-openai-pe"
  location            = var.private_endpoint_location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id
  private_service_connection {
    name                           = "${azurerm_cognitive_account.main.name}_privateserviceconnection"
    private_connection_resource_id = azurerm_cognitive_account.main.id
    is_manual_connection           = false
    subresource_names              = ["account"]
  }
  tags = var.common_tags
  lifecycle {
    ignore_changes = [tags, private_dns_zone_group]
  }
}

# -------------
# Access from Azure AI Search
# -------------
# Search calls OpenAI from its own multi-tenant infrastructure, not from the VNet, so with public
# access disabled it needs a shared private link (a Search-managed private endpoint to the account).
resource "azurerm_search_shared_private_link_service" "openai" {
  name               = "${var.app_name}-openai-spl"
  search_service_id  = var.search_service_id
  subresource_name   = "openai_account"
  target_resource_id = azurerm_cognitive_account.main.id
  request_message    = local.shared_private_link_request_message

  depends_on = [azurerm_cognitive_deployment.embedding]
}

locals {
  shared_private_link_request_message = "Azure AI Search ${var.app_name} access to ${var.app_name}-openai"
}

# A shared private link always arrives as Pending on the target resource and azurerm cannot
# approve it, so approve it with the az CLI (logged in by azure/login in .deployer_aca.yml).
# Runs once per shared private link; only approves the connection carrying our request message.
resource "terraform_data" "approve_shared_private_link" {
  triggers_replace = [azurerm_search_shared_private_link_service.openai.id]

  provisioner "local-exec" {
    interpreter = ["bash", "-c"]
    environment = {
      OPENAI_ACCOUNT_ID = azurerm_cognitive_account.main.id
      REQUEST_MESSAGE   = local.shared_private_link_request_message
      MSYS_NO_PATHCONV  = "1" # Git Bash on Windows would otherwise rewrite /subscriptions/... into a file path
    }
    command = <<-EOT
      set -euo pipefail
      ids=$(az network private-endpoint-connection list --id "$OPENAI_ACCOUNT_ID" \
        --query "[?properties.privateLinkServiceConnectionState.status=='Pending' && properties.privateLinkServiceConnectionState.description=='$REQUEST_MESSAGE'].id" \
        -o tsv | tr -d '\r')
      if [ -z "$ids" ]; then
        echo "No pending shared private link connection to approve."
        exit 0
      fi
      for id in $ids; do
        echo "Approving $id"
        az network private-endpoint-connection approve --id "$id" \
          --description "Approved by Terraform for Azure AI Search" > /dev/null
      done
    EOT
  }
}

# Search authenticates to OpenAI with its system-assigned managed identity (no API key in the
# vectorizer / skillset definition).
resource "azurerm_role_assignment" "search_openai_user" {
  scope                = azurerm_cognitive_account.main.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = var.search_principal_id
  principal_type       = "ServicePrincipal"
}
