# Development Container Setup

This repository includes a VS Code development container configuration that provides a complete development environment with:

## Included Tools

- **Node.js 20** - JavaScript/TypeScript runtime
- **TypeScript** - Type-safe JavaScript development
- **Azure CLI** - Command-line interface for Azure
- **Terraform** - Infrastructure as Code tool
- **Azure Functions Core Tools** - Local Azure Functions development
- **Cosmos DB Emulator** - Local Cosmos DB development

## VS Code Extensions

The devcontainer includes these pre-installed extensions:

- HashiCorp Terraform - Terraform language support
- Azure Account - Azure authentication
- Azure Functions - Azure Functions development
- Azure Resource Groups - Azure resource management
- Azure App Service - App Service management
- Azure Cosmos DB - Cosmos DB management
- Azure Terraform - Terraform Azure integration

## Getting Started

1. **Prerequisites:**
   - VS Code with the "Dev Containers" extension installed
   - Docker Desktop running on your machine

2. **Open in Container:**
   - Open this folder in VS Code
   - Click "Reopen in Container" when prompted, or
   - Use Command Palette (F1) → "Dev Containers: Reopen in Container"

3. **First Time Setup:**
   - The container will build automatically (may take a few minutes)
   - Dependencies will be installed automatically via `postCreateCommand`

## Services

### Cosmos DB Emulator
- **URL:** https://localhost:8081/_explorer/index.html
- **Key:** `C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==`
- **Connection String:** `AccountEndpoint=https://localhost:8081/;AccountKey=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==`

## Useful Commands

The container includes these helpful aliases:

```bash
# Terraform shortcuts
tf          # terraform
tfi         # terraform init
tfp         # terraform plan
tfa         # terraform apply

# List files
ll          # ls -la
```

## Port Forwarding

The following ports are automatically forwarded:

- **7071** - Azure Functions runtime
- **3000** - Development server
- **8080** - API server
- **8081** - Cosmos DB Emulator

## Azure Authentication

Your local Azure CLI credentials are mounted into the container, so you should be able to use `az` commands without re-authenticating.

## Development Workflow

1. **Infrastructure Development:**
   ```bash
   cd infra
   terraform init
   terraform plan
   terraform apply
   ```

2. **API Development:**
   ```bash
   cd src/api
   npm install
   npm run dev
   ```

3. **Functions Development:**
   ```bash
   cd src
   func start
   ```

## Troubleshooting

- **Container won't start:** Ensure Docker Desktop is running
- **Cosmos DB not accessible:** Wait for the health check to pass (may take 1-2 minutes)
- **Azure CLI not authenticated:** Run `az login` in the container terminal
- **Port conflicts:** Check if ports 8081, 7071, 3000, or 8080 are already in use

## Customization

You can modify the devcontainer configuration in `.devcontainer/`:

- `devcontainer.json` - Main configuration
- `Dockerfile` - Custom container setup
- `docker-compose.yml` - Multi-service setup
