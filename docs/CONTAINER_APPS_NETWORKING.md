# Azure Container Apps Networking Requirements

## Critical Requirement: Dedicated Subnet

**Azure Container Apps Environment requires a dedicated subnet that cannot be shared with any other Azure resources.**

### Why Container Apps Cannot Share Subnets

Container Apps needs to:
1. Delegate the subnet to `Microsoft.App/environments`
2. Have exclusive control over the subnet for infrastructure components
3. Manage internal networking and service mesh independently

### Error When Sharing Subnets

```
ManagedEnvironmentInvalidNetworkConfiguration: The environment network configuration is invalid: 
The delegated subnet cannot be used by any other Azure resources.
```

## Subnet Configuration

### Test/Prod Environments (deploy_network = true)

The network module automatically creates **3 dedicated subnets**:

| Subnet | CIDR | Purpose | Delegation |
|--------|------|---------|------------|
| `app-service-subnet` | `.0/27` (32 IPs) | App Service VNet integration | `Microsoft.Web/serverFarms` |
| `private-endpoints-subnet` | `.32/28` (16 IPs) | Private endpoints (Cosmos, Storage, etc.) | None |
| `container-apps-subnet` | `.48/28` (16 IPs) | Container Apps Environment | `Microsoft.App/environments` |

### Dev Environment (deploy_network = false)

**Container Apps deployment is NOT SUPPORTED in dev environment** because:
- Dev uses existing VNet with pre-allocated subnets
- All existing subnets are already in use (private endpoints, app services, etc.)
- Creating a new subnet would require network team approval and coordination

**Solution for Dev:**
- Use `deployment_type = "app_service"` (default)
- Test Container Apps in **test or prod environments** where subnets are created automatically

## Deployment Type Selection

### For Dev Environment
```hcl
# terragrunt/dev/terragrunt.hcl
inputs = {
  deploy_network = false
  deployment_type = "app_service"  # Must use App Service in dev
}
```

### For Test/Prod Environments
```hcl
# terragrunt/test/terragrunt.hcl or terragrunt/prod/terragrunt.hcl
inputs = {
  deploy_network = true
  deployment_type = "container_apps"  # Can use Container Apps
}
```

## Workflows

### App Service Deployment
- **Workflows:** `deploy-to-dev.yml`, `deploy-to-test.yml`
- **Environments:** Dev, Test, Prod
- **Subnet:** Uses existing `dev_app_service_subnet_id` in dev, or `app-service-subnet` in test/prod

### Container Apps Deployment
- **Workflows:** `deploy-aca-dev.yml`, `deploy-aca-test.yml`
- **Environments:** Test, Prod only (NOT dev)
- **Subnet:** Requires `container-apps-subnet` created by network module

## Network Security

### Container Apps Security Model

Since Container Apps doesn't support IP service tags (like `AzureFrontDoor.Backend`), security is enforced through:

1. **Internal-only ingress** (`external_enabled = false`)
   - Container App is not publicly accessible
   - Only accessible from within the VNet

2. **VNet Integration**
   - Deployed into dedicated subnet with delegation
   - Isolated from other resources

3. **Network Security Group**
   - Controls traffic between Container Apps subnet and other subnets
   - Allows communication with private endpoints
   - Allows outbound HTTPS for dependencies

4. **Front Door as Entry Point**
   - Front Door connects to Container App via private network
   - Public users → Front Door → VNet → Container App

### NSG Rules for Container Apps

```hcl
# Allow traffic from Private Endpoints to Container Apps
- Inbound: private_endpoints_subnet → container_apps_subnet

# Allow Container Apps to access Private Endpoints (Cosmos, Storage, etc.)
- Outbound: container_apps_subnet → private_endpoints_subnet

# Allow Container Apps to access internet (for pulling images, calling external APIs)
- Outbound: container_apps_subnet → Internet (ports 80, 443)
```

## Migration Path

If you need to test Container Apps in dev environment:

### Option 1: Create New Subnet (Requires Network Team)
1. Request new subnet from network team (e.g., `.64/28`)
2. Add subnet delegation to `Microsoft.App/environments`
3. Add `dev_container_apps_subnet_id` to `terragrunt/dev/terragrunt.hcl`
4. Update `infra/main.tf` to support dev Container Apps subnet

### Option 2: Use Test Environment (Recommended)
1. Deploy Container Apps to **test environment** using `deploy-aca-test.yml` workflow
2. Test environment creates subnets automatically
3. No manual networking coordination required

## Summary

✅ **Container Apps in Test/Prod:** Fully supported with automatic subnet creation

❌ **Container Apps in Dev:** Not supported (use App Service instead)

🔄 **Conditional Deployment:** Use `deployment_type` variable to choose between App Service and Container Apps
