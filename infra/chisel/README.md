# Azure Chisel Proxy Configuration

This directory contains the Chisel proxy configuration for secure tunneling to Azure services (e.g., PostgreSQL databases).

## Overview

Chisel is a fast TCP/UDP tunnel over HTTP that provides:
- Secure tunneling via HTTPS with mandatory authentication
- Local port forwarding to remote services
- Health checks for monitoring and orchestration
- Container-native deployment
- Automatic restart with retry logic

## Architecture

```
Local Machine (Port 5462)
        ↓
Chisel Client
        ↓
HTTPS Connection
        ↓
Azure Web App (Chisel Server)
        ↓
Azure PostgreSQL (or other service)
```

## Files

- **Dockerfile**: Multi-stage Docker image for the Chisel server
- **start-chisel.sh**: Startup script that orchestrates server initialization
- **healthz.json**: Health check response template

## Local Development Setup

### Prerequisites

- Docker installed and running
- Access to the Azure Chisel server endpoint
- Chisel authentication token

### Running Locally with Docker

```bash
docker run --rm -it -p 5462:5432 jpillora/chisel:latest client \
  --auth "tunnel:YOUR_AUTH_TOKEN" \
  https://your-chisel-server.azurewebsites.net \
  0.0.0.0:5432:your-postgres-server.postgres.database.azure.com:5432
```

### Connecting to the Proxied Database

Once the Chisel tunnel is running:

```bash
psql -h localhost -p 5462 -U postgres -d your_database
```

Or in your application configuration:

```
Database Host: localhost
Port: 5462
Username: postgres
Database: your_database
```

## Docker Build and Run

### Build the Image

```bash
docker build -t nr-ai-form-chisel:latest .
```

### Run as Server

```bash
docker run -d \
  --name chisel-proxy \
  -p 80:80 \
  -p 9999:9999 \
  -e CHISEL_AUTH="tunnel:your-secure-password" \
  -e CHISEL_HOST="0.0.0.0" \
  -e CHISEL_PORT="80" \
  -e CHISEL_ENABLE_SOCKS5="true" \
  -e MAX_RETRIES="30" \
  -e DELAY_SECONDS="5" \
  nr-ai-form-chisel:latest
```

## Environment Variables

### Chisel Configuration

- **CHISEL_AUTH** (required): Authentication credentials in format `username:password`
  - Example: `tunnel:YourSecurePasswordHere`
  - Required for secure connections

- **CHISEL_PORT** (optional): Port the Chisel server listens on
  - Default: `80`
  - Must match the exposed port in containers

- **CHISEL_HOST** (optional): Host address to bind to
  - Default: `0.0.0.0` (all interfaces)

- **CHISEL_ENABLE_SOCKS5** (optional): Enable SOCKS5 proxy support
  - Default: `true`
  - Set to `false` if SOCKS5 is not needed

- **CHISEL_EXTRA_ARGS** (optional): Additional Chisel server arguments
  - For advanced configuration

### Health Monitoring

- **MAX_RETRIES** (optional): Maximum retry attempts on failure
  - Default: `30`

- **DELAY_SECONDS** (optional): Delay between retries in seconds
  - Default: `5`

- **PORT** (optional): Alias for CHISEL_PORT
  - Used by Azure App Service

## Startup Process

The `start-chisel.sh` script performs the following steps:

1. **Validates Chisel binary**: Ensures Chisel is available
2. **Starts health backend**: Launches HTTP server on port 9999 for health checks
3. **Starts Chisel server**: Launches the tunnel server with configured authentication
4. **Reverse-proxy health**: Chisel reverse-proxies `/healthz` requests to health backend
5. **Retry logic**: Automatically restarts on failure (up to `MAX_RETRIES` times)
6. **Graceful shutdown**: Responds to termination signals and cleans up processes

## Health Checks

### Health Endpoint

```
GET /healthz
```

Response:
```json
{
  "status": "healthy"
}
```

### Azure App Service Integration

The health check is available at:
```
http://your-app-service.azurewebsites.net/healthz
```

## Security Considerations

### Authentication

- **Always set CHISEL_AUTH** with a strong password in production
- Use format: `username:password` (e.g., `tunnel:YourSecurePasswordHere`)
- Store the password securely in Azure Key Vault

### Network Security

- The proxy should only be accessible from trusted networks
- Restrict inbound access using IP restrictions on App Service
- Use HTTPS for all client connections to the proxy
- Place behind Azure Front Door or Application Gateway when possible

### Database Access

- The proxy does not store or log database credentials
- PostgreSQL credentials are handled separately on the client side
- Always use encrypted connections (SSL/TLS) when available

## Monitoring and Logs

### Application Insights

The proxy sends logs and metrics to Application Insights when configured:

- HTTP request logs
- Container logs
- Platform diagnostics
- Performance metrics

View logs in Azure Portal:
1. Navigate to the App Service resource
2. Go to Application Insights → Application Map or Logs

### Container Logs

View real-time logs in Azure Portal:
```
App Service → Log stream
```

Or via Azure CLI:
```bash
az webapp log tail --resource-group <rg-name> --name <web-app-name>
```

## Troubleshooting

### Connection Refused

**Problem**: `Connection refused` when connecting to `localhost:5462`

**Solution**:
- Verify the Chisel tunnel is running: `docker ps`
- Check the port mapping: `-p 5462:5432` must be in the docker command
- Ensure the Azure proxy endpoint is reachable

### Authentication Failed

**Problem**: `Authorization failed` or `Auth failed` in logs

**Solution**:
- Verify the `--auth` parameter matches the server's `CHISEL_AUTH` setting
- Ensure the password is correct and not expired
- Check Azure Key Vault for the current credentials

### Cannot Resolve Hostname

**Problem**: `Cannot resolve hostname 'xxxxx.database.azure.com'`

**Solution**:
- Verify the Azure proxy server has network access to the database
- Check Network Security Group (NSG) rules allow outbound traffic on port 5432
- Ensure the database server name is correct

### High Latency

**Problem**: Slow database connections through the proxy

**Solution**:
- Chisel adds minimal overhead; check the Azure App Service plan tier
- Upgrade to a higher SKU (B2, B3, S1) if running on B1
- Check network latency between regions

## Deployment to Azure

This Chisel proxy is deployed as an Azure App Service using Infrastructure as Code (Terraform). Key resources:

- App Service Plan: Linux-based hosting for the proxy container
- Web App: Runs the Chisel server container
- Application Insights: Monitoring and diagnostics
- Virtual Network Integration: Securely connects to your VNet

See the main `infra/` directory for Terraform modules.

## References

- [Chisel GitHub Repository](https://github.com/jpillora/chisel)
- [Azure App Service Documentation](https://docs.microsoft.com/azure/app-service/)
- [Azure PostgreSQL Documentation](https://docs.microsoft.com/azure/postgresql/)
- [Azure Key Vault for Secrets Management](https://docs.microsoft.com/azure/key-vault/)
