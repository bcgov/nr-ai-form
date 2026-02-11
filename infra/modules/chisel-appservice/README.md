# Chisel Proxy Azure App Service Terraform Module

This Terraform module deploys the Chisel proxy to Azure App Service instead of Container Apps.

## Features

- Deploys Chisel as an Azure App Service with Linux runtime
- Docker container support with ACR integration
- Auto-scaling support (configurable, 1-3 replicas by default)
- Managed identity for secure access to other Azure services
- Health checks and diagnostics logging
- HTTPS enforcement
- Cost-effective alternative to Container Apps

## Benefits Over Container Apps

- Lower cost for stable, long-running workloads
- Simpler scaling model
- Better suited for always-on proxy services
- Integrated with App Service ecosystem

## Prerequisites

1. Azure Container Registry (ACR) with Chisel Docker image
2. Log Analytics Workspace for diagnostics
3. Resource Group created
4. Docker image: `<acr-name>.azurecr.io/nr-ai-form-chisel:latest`

## Usage

### Basic Usage

```hcl
module "chisel_proxy" {
  source = "./modules/chisel-appservice"

  app_service_name           = "chisel-proxy"
  app_service_plan_name      = "chisel-proxy-plan"
  location                   = "eastus"
  resource_group_name        = azurerm_resource_group.main.name
  
  sku_name                   = "B2"  # B1, B2, P1V2, etc.
  docker_image_name          = "nr-ai-form-chisel:latest"
  
  registry_server            = "${var.acr_name}.azurecr.io"
  registry_username          = var.acr_username
  registry_password          = var.acr_password

  chisel_password            = var.chisel_password
  chisel_port                = "8080"
  enable_socks5              = true

  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  
  enable_autoscale           = true
  min_instances              = 1
  max_instances              = 3

  common_tags                = var.common_tags
}
```

### In Your Root main.tf

```hcl
# Replace or update the chisel_proxy module call

module "chisel_proxy" {
  source = "./modules/chisel-appservice"

  app_service_name           = "chisel-proxy"
  app_service_plan_name      = "chisel-proxy-plan"
  location                   = var.location
  resource_group_name        = azurerm_resource_group.main.name
  
  sku_name                   = var.chisel_sku_name  # Default: B2
  docker_image_name          = "${var.acr_name}/nr-ai-form-chisel:latest"
  
  registry_server            = "${var.acr_name}.azurecr.io"
  registry_username          = var.acr_username
  registry_password          = var.acr_password

  chisel_password            = var.chisel_password
  
  log_analytics_workspace_id = module.monitoring.log_analytics_workspace_id

  common_tags                = var.common_tags

  depends_on = [
    azurerm_resource_group.main,
    module.monitoring
  ]
}

# Output the Chisel URL to your outputs.tf
output "chisel_proxy_url" {
  value       = module.chisel_proxy.chisel_url
  description = "Public URL of the Chisel proxy"
}

output "chisel_proxy_fqdn" {
  value       = module.chisel_proxy.chisel_fqdn
  description = "FQDN of the Chisel proxy"
}
```

### In Your terraform.tfvars

```hcl
# Update these variables
chisel_password    = "YourSecurePasswordHere!"
acr_name           = "nraiformacr"
acr_username       = "admin"
acr_password       = "your-acr-password"
chisel_sku_name    = "B2"  # Options: B1, B2, B3, P1V2, P2V2, P3V2, etc.
```

## SKU Options

### Budget-Friendly (B-Series)
- **B1**: 1 vCPU, 1.75 GB RAM - for low-traffic
- **B2**: 2 vCPUs, 3.5 GB RAM - recommended for proxy workloads
- **B3**: 4 vCPUs, 7 GB RAM - for higher traffic

### Premium (P-Series)
- **P1V2**: 1 vCPU, 3.5 GB RAM
- **P2V2**: 2 vCPUs, 7 GB RAM
- **P3V2**: 4 vCPUs, 14 GB RAM

Recommendation: Use **B2** for stable proxy workloads with good balance of cost and performance.

## Outputs

- `chisel_app_service_name` - Name of the Chisel App Service
- `chisel_app_service_id` - Resource ID of the App Service
- `chisel_fqdn` - FQDN of the Chisel proxy
- `chisel_url` - Full HTTPS URL of the Chisel proxy
- `health_check_url` - URL for health checks
- `app_service_plan_id` - Resource ID of the App Service Plan
- `principal_id` - Managed identity principal ID (for Key Vault access, etc.)

## Environment Variables

The module configures these environment variables automatically:

| Variable | Source | Example |
|----------|--------|---------|
| DOCKER_REGISTRY_SERVER_URL | ACR | https://myacr.azurecr.io |
| DOCKER_REGISTRY_SERVER_USERNAME | Input | (ACR admin username) |
| DOCKER_REGISTRY_SERVER_PASSWORD | Input | (ACR admin password) |
| WEBSITES_PORT | var.chisel_port | 8080 |
| CHISEL_AUTH | var.chisel_password | tunnel:mypassword |
| CHISEL_PORT | var.chisel_port | 8080 |
| CHISEL_HOST | var.chisel_host | 0.0.0.0 |
| CHISEL_ENABLE_SOCKS5 | var.enable_socks5 | true/false |
| PORT | var.chisel_port | 8080 |
| MAX_RETRIES | var.max_retries | 30 |
| DELAY_SECONDS | var.delay_seconds | 5 |

## Auto-Scaling

When `enable_autoscale` is true, the module configures:

- **Scale Up**: When CPU > 70% for 5 minutes, add 1 instance
- **Scale Down**: When CPU < 30% for 5 minutes, remove 1 instance
- **Cooldown**: 5 minutes between scaling operations
- **Range**: min_instances to max_instances

## Monitoring & Diagnostics

The module automatically enables:

- App Service HTTP Logs
- Console Logs
- Metrics collection
- Log Analytics integration (logs sent to specified workspace)

## Health Checks

Health check endpoint: `https://<app-service-url>/` (customizable via `health_check_path`)

Azure App Service will monitor this endpoint and mark the app unhealthy if it returns non-2xx status.

## Client Connection

Once deployed, connect your Chisel client:

```bash
# Basic tunnel
docker run jpillora/chisel:latest client --auth "tunnel:PASSWORD" \
  https://<chisel-fqdn> \
  localhost:5432:database-host:5432

# SOCKS5 proxy
docker run jpillora/chisel:latest client --auth "tunnel:PASSWORD" \
  https://<chisel-fqdn> \
  socks
```

## Testing

```bash
# Test HTTPS connectivity
curl -v https://<chisel-fqdn>/

# Check App Service logs
az webapp log tail --name <app-service-name> --resource-group <resource-group-name>

# Stream logs in real-time
az webapp log tail --name <app-service-name> --resource-group <resource-group-name> -f
```

## Troubleshooting

### App Service won't start
- Check Docker image is available in ACR
- Verify registry credentials are correct
- Check Application logs: `az webapp log show --name <app-name> --resource-group <rg-name>`

### Connection issues
- Verify HTTPS is working: `curl -v https://<fqdn>`
- Check network security groups if App Service is in a VNet
- Ensure chisel_port matches Docker image's exposed port

### High CPU usage
- Increase SKU to larger instance size
- Adjust auto-scale thresholds in main.tf
- Monitor with: `az monitor metrics list --resource <app-service-id>`

## Migration from Container Apps

To migrate from the Container Apps module:

1. Update `infra/main.tf` to use this module instead of `chisel-proxy`
2. Update `terraform.tfvars` with the new variables
3. Run `terraform plan` to review changes
4. Run `terraform apply` to deploy
5. Update client configurations to point to new FQDN

## Cost Estimation

| SKU | Monthly Cost (approx) | Use Case |
|-----|----------------------|----------|
| B1  | $10-15               | Development/low traffic |
| B2  | $30-50               | Production proxy |
| B3  | $60-80               | High-traffic proxy |
| P1V2 | $70-90              | Premium workloads |

Costs vary by region. Use Azure Pricing Calculator for accurate estimates.

## Related Modules

- `./modules/container-apps` - Deprecated for Chisel deployment
- `./modules/monitoring` - Provides log_analytics_workspace_id
- `./modules/network` - Optional VNet integration

## Support

For issues or questions about Chisel proxy configuration, see:
- [Chisel GitHub](https://github.com/jpillora/chisel)
- [Azure App Service Documentation](https://docs.microsoft.com/en-us/azure/app-service/)
