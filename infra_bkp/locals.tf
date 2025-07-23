locals {
  # get json 
  abbrs = jsondecode(file("${path.module}/naming/abbreviations.json"))

  apim_nsg_security_rules = {
    "Client_communication_to_API_Management" = {
      name                       = "Client_communication_to_API_Management"
      priority                   = 100
      direction                  = "Inbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_range     = "80"
      source_address_prefix      = "Internet"
      destination_address_prefix = "VirtualNetwork"
    }
    "Secure_Client_communication_to_API_Management" = {
      name                       = "Secure_Client_communication_to_API_Management"
      priority                   = 110
      direction                  = "Inbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_range     = "443"
      source_address_prefix      = "Internet"
      destination_address_prefix = "VirtualNetwork"
    }
    "Management_endpoint_for_Azure_portal_and_Powershell" = {
      name                       = "Management_endpoint_for_Azure_portal_and_Powershell"
      priority                   = 120
      direction                  = "Inbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_range     = "3443"
      source_address_prefix      = "ApiManagement"
      destination_address_prefix = "VirtualNetwork"
    }
    "Dependency_on_Redis_Cache" = {
      name                       = "Dependency_on_Redis_Cache"
      priority                   = 130
      direction                  = "Inbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_range     = "6381-6383"
      source_address_prefix      = "VirtualNetwork"
      destination_address_prefix = "VirtualNetwork"
    }
    "Dependency_to_sync_Rate_Limit_Inbound" = {
      name                       = "Dependency_to_sync_Rate_Limit_Inbound"
      priority                   = 135
      direction                  = "Inbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_range     = "4290"
      source_address_prefix      = "VirtualNetwork"
      destination_address_prefix = "VirtualNetwork"
    }
    "Dependency_on_Azure_SQL" = {
      name                       = "Dependency_on_Azure_SQL"
      priority                   = 140
      direction                  = "Outbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_range     = "1433"
      source_address_prefix      = "VirtualNetwork"
      destination_address_prefix = "Sql"
    }
    "Dependency_for_Log_to_event_Hub_policy" = {
      name                       = "Dependency_for_Log_to_event_Hub_policy"
      priority                   = 150
      direction                  = "Outbound"
      access                     = "Allow"
      protocol                   = "*"
      source_port_range          = "*"
      destination_port_range     = "5671"
      source_address_prefix      = "VirtualNetwork"
      destination_address_prefix = "EventHub"
    }
    "Dependency_on_Redis_Cache_outbound" = {
      name                       = "Dependency_on_Redis_Cache_outbound"
      priority                   = 160
      direction                  = "Outbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_range     = "6381-6383"
      source_address_prefix      = "VirtualNetwork"
      destination_address_prefix = "VirtualNetwork"
    }
    "Dependency_To_sync_RateLimit_Outbound" = {
      name                       = "Dependency_To_sync_RateLimit_Outbound"
      priority                   = 165
      direction                  = "Outbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_range     = "4290"
      source_address_prefix      = "VirtualNetwork"
      destination_address_prefix = "VirtualNetwork"
    }
    "Dependency_on_Azure_File_Share_for_GIT" = {
      name                       = "Dependency_on_Azure_File_Share_for_GIT"
      priority                   = 170
      direction                  = "Outbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_range     = "445"
      source_address_prefix      = "VirtualNetwork"
      destination_address_prefix = "Storage"
    }
    "Azure_Infrastructure_Load_Balancer" = {
      name                       = "Azure_Infrastructure_Load_Balancer"
      priority                   = 180
      direction                  = "Inbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_range     = "6390"
      source_address_prefix      = "AzureLoadBalancer"
      destination_address_prefix = "VirtualNetwork"
    }
    "Publish_DiagnosticLogs_And_Metrics" = {
      name                       = "Publish_DiagnosticLogs_And_Metrics"
      description                = "API Management logs and metrics for consumption by admins and your IT team are all part of the management plane"
      priority                   = 185
      direction                  = "Outbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_ranges    = ["443", "12000", "1886"]
      source_address_prefix      = "VirtualNetwork"
      destination_address_prefix = "AzureMonitor"
    }
    "Connect_To_SMTP_Relay_For_SendingEmails" = {
      name                       = "Connect_To_SMTP_Relay_For_SendingEmails"
      description                = "APIM features the ability to generate email traffic as part of the data plane and the management plane"
      priority                   = 190
      direction                  = "Outbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_ranges    = ["25", "587", "25028"]
      source_address_prefix      = "VirtualNetwork"
      destination_address_prefix = "Internet"
    }
    "Authenticate_To_Azure_Active_Directory" = {
      name                       = "Authenticate_To_Azure_Active_Directory"
      description                = "Connect to Azure Active Directory for developer Portal authentication or for OAuth 2 flow during any proxy authentication"
      priority                   = 200
      direction                  = "Outbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_ranges    = ["80", "443"]
      source_address_prefix      = "VirtualNetwork"
      destination_address_prefix = "AzureActiveDirectory"
    }
    "Dependency_on_Azure_Storage" = {
      name                       = "Dependency_on_Azure_Storage"
      description                = "API Management service dependency on Azure blob and Azure table storage"
      priority                   = 100
      direction                  = "Outbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_range     = "443"
      source_address_prefix      = "VirtualNetwork"
      destination_address_prefix = "Storage"
    }
    "Publish_Monitoring_Logs" = {
      name                       = "Publish_Monitoring_Logs"
      priority                   = 300
      direction                  = "Outbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_range     = "443"
      source_address_prefix      = "VirtualNetwork"
      destination_address_prefix = "AzureCloud"
    }
    "Deny_All_Internet_Outbound" = {
      name                       = "Deny_All_Internet_Outbound"
      priority                   = 999
      direction                  = "Outbound"
      access                     = "Deny"
      protocol                   = "*"
      source_port_range          = "*"
      destination_port_range     = "*"
      source_address_prefix      = "VirtualNetwork"
      destination_address_prefix = "Internet"
    }
  }

  app_service_nsg_security_rules = {
    
  }

  privateendpoints_nsg_security_rules = {
    
  }

  apim_route_table_routes = {
    "ApimMgmtEndpointToApimServiceTag" = {
    name                   = "ApimMgmtEndpointToApimServiceTag"
    address_prefix         = "ApiManagement"
    next_hop_type          = "Internet"
    }
    "ApimToInternet" = {
    name                   = "ApimToInternet"
    address_prefix         = "0.0.0.0/0"
    next_hop_type          = "Internet"
    }
  }
}