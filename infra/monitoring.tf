resource "azurerm_log_analytics_workspace" "example" {
  name                = "${local.abbrs.operationalInsightsWorkspaces}${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
    lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_application_insights" "app_insights" {
  name                = "${local.abbrs.insightsComponents}${random_id.random_deployment_suffix.hex}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.example.id
    lifecycle {
    ignore_changes = [tags]
  }
}