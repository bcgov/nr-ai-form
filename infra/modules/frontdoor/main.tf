resource "azurerm_cdn_frontdoor_profile" "frontend_frontdoor" {
  name                = "${var.app_name}-frontend-frontdoor"
  resource_group_name = var.resource_group_name
  sku_name            = "Premium_AzureFrontDoor"

  tags = var.common_tags
  lifecycle {
    ignore_changes = [
      # Ignore tags to allow management via Azure Policy
      tags
    ]
  }
}

resource "azurerm_cdn_frontdoor_firewall_policy" "frontend_firewall_policy" {
  name                = "${replace(var.app_name, "/[^a-zA-Z0-9]/", "")}frontendfirewall"
  resource_group_name = var.resource_group_name
  sku_name            = var.frontdoor_sku_name
  mode                = "Prevention"

  log_scrubbing {
    enabled = true

    scrubbing_rule {
      enabled        = true
      match_variable = "RequestHeaderNames"
      operator       = "Equals"
      selector       = "Authorization"
    }
  }
  # the 'managed_rule' code block is only supported with the "Premium_AzureFrontDoor" sku
  dynamic "managed_rule" {
    for_each = var.frontdoor_sku_name == "Premium_AzureFrontDoor" ? [1] : []
    content {
      type    = "DefaultRuleSet"
      version = "1.0"
      action  = "Log"

      # The browser WebSocket handshake is wss://<fd>/ws?session_id=<id>. DRS 1.0 session-fixation
      # rules block any request with a "session_id" query arg name and no/off-domain Referer
      # (browsers send no Referer on the handshake), returning 403 before the API is reached.
      # The API uses no cookie sessions, so log these instead of blocking. The rule-set level
      # action = "Log" above is not applied by DRS 1.0, so the override has to be per rule.
      override {
        rule_group_name = "FIX"
        rule {
          rule_id = "943110" # SessionID Parameter Name with Off-Domain Referer
          enabled = true
          action  = "Log"
        }
        rule {
          rule_id = "943120" # SessionID Parameter Name with No Referer
          enabled = true
          action  = "Log"
        }
      }
    }
  }
  dynamic "managed_rule" {
    for_each = var.frontdoor_sku_name == "Premium_AzureFrontDoor" ? [1] : []
    content {
      type    = "Microsoft_BotManagerRuleSet"
      version = "1.1"
      action  = "Block"
    }
  }
  custom_rule {
    name                           = "RateLimitByIP"
    enabled                        = true
    priority                       = 1
    type                           = "RateLimitRule"
    rate_limit_duration_in_minutes = 1
    rate_limit_threshold           = 10
    action                         = "Block"
    match_condition {
      match_variable     = "RemoteAddr"
      operator           = "IPMatch"
      negation_condition = false
      match_values       = ["0.0.0.0/0"] # Apply to all IPs
    }
  }
  tags = var.common_tags
  lifecycle {
    ignore_changes = [
      # Ignore tags to allow management via Azure Policy
      tags
    ]
  }
}


