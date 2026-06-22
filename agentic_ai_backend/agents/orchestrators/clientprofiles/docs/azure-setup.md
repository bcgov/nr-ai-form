# Azure Cosmos DB Setup Guide

This document describes how to provision and configure Azure Cosmos DB for the multitenancy layer, including the production Azure account, RBAC role assignments, seed data import, and local Cosmos emulator setup.

---

## Table of Contents

1. [Cosmos DB Account Creation](#1-cosmos-db-account-creation)
2. [Database and Container Creation](#2-database-and-container-creation)
3. [Sample Azure CLI Provisioning Script](#3-sample-azure-cli-provisioning-script)
4. [Seed Data Import](#4-seed-data-import)
5. [RBAC Role Assignment (Managed Identity)](#5-rbac-role-assignment-managed-identity)
6. [Local Cosmos Emulator Setup (docker-compose)](#6-local-cosmos-emulator-setup-docker-compose)

---

## 1. Cosmos DB Account Creation

Create an Azure Cosmos DB account with the following settings:

| Setting | Value |
|---------|-------|
| API | Core (SQL) / NoSQL |
| Consistency Level | Session |
| Region | Canada Central |
| Capacity Mode | Serverless (recommended for dev) or Provisioned |

### Portal

1. Navigate to **Azure Portal → Create a resource → Azure Cosmos DB**.
2. Select **Azure Cosmos DB for NoSQL**.
3. Fill in:
   - **Subscription**: your subscription
   - **Resource Group**: your resource group (e.g. `rg-nr-ai-form-dev`)
   - **Account Name**: e.g. `cosmos-nr-ai-form-dev`
   - **Location**: Canada Central
   - **Capacity mode**: Serverless (or Provisioned with autoscale)
4. Under **Global Distribution**, keep defaults (single region for dev).
5. Under **Consistency**, select **Session**.
6. Review + Create.

---

## 2. Database and Container Creation

Once the account is provisioned, create the database and container:

| Resource | Name | Notes |
|----------|------|-------|
| Database | `AgentMemoryDB` | Or operator-chosen name (set via `AZURE_COSMOS_DB_DATABASE_NAME` env var) |
| Container | `ClientProfiles` | Partition key: `/clientId` |

### Portal

1. Open the Cosmos DB account in the Portal.
2. **Data Explorer → New Database** → name: `AgentMemoryDB`.
3. **New Container** inside `AgentMemoryDB`:
   - Container ID: `ClientProfiles`
   - Partition key: `/clientId`
   - Leave indexing policy at default (or customise as needed).

---

## 3. Sample Azure CLI Provisioning Script

The following script creates the Cosmos DB account, database, and container with the correct settings. Adjust variables to match your environment.

```bash
#!/usr/bin/env bash
# azure-setup.sh — Provision Cosmos DB for the multitenancy layer
# Usage: bash azure-setup.sh

set -euo pipefail

# ─── Configuration ────────────────────────────────────────────────────────────
RESOURCE_GROUP="rg-nr-ai-form-dev"
LOCATION="canadacentral"
ACCOUNT_NAME="cosmos-nr-ai-form-dev"
DATABASE_NAME="AgentMemoryDB"
CONTAINER_NAME="ClientProfiles"
PARTITION_KEY="/clientId"

# ─── Create Cosmos DB Account (Core SQL API, Session consistency) ─────────────
echo "Creating Cosmos DB account: $ACCOUNT_NAME ..."
az cosmosdb create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACCOUNT_NAME" \
  --kind "GlobalDocumentDB" \
  --locations regionName="$LOCATION" failoverPriority=0 isZoneRedundant=false \
  --default-consistency-level "Session" \
  --capabilities "EnableServerless"

# ─── Create Database ─────────────────────────────────────────────────────────
echo "Creating database: $DATABASE_NAME ..."
az cosmosdb sql database create \
  --resource-group "$RESOURCE_GROUP" \
  --account-name "$ACCOUNT_NAME" \
  --name "$DATABASE_NAME"

# ─── Create Container with partition key /clientId ────────────────────────────
echo "Creating container: $CONTAINER_NAME (partition key: $PARTITION_KEY) ..."
az cosmosdb sql container create \
  --resource-group "$RESOURCE_GROUP" \
  --account-name "$ACCOUNT_NAME" \
  --database-name "$DATABASE_NAME" \
  --name "$CONTAINER_NAME" \
  --partition-key-path "$PARTITION_KEY"

echo "Done. Cosmos DB infrastructure provisioned."
```

> **Note:** Remove `--capabilities "EnableServerless"` if using provisioned throughput mode. For provisioned mode, add `--throughput 400` (or `--max-throughput 4000` for autoscale) to the container create command.

---

## 4. Seed Data Import

The seed data file is located at:

```
clientprofiles/seed/client_profiles.json
```

It contains three pre-seeded tenant profiles:

| clientId | clientName |
|----------|------------|
| `11111111-1111-4111-8111-111111111111` | Water Permit App |
| `22222222-2222-4222-8222-222222222222` | Fishing Permit App |
| `33333333-3333-4333-8333-333333333333` | Example App |

Each profile conforms to the `ClientProfile` document structure:

```json
{
  "id": "<clientId GUID>",
  "clientId": "<same GUID>",
  "clientName": "...",
  "corsOrigins": ["..."],
  "tenantResources": {
    "blobConnectionString": "...",
    "containerName": "...",
    "prompts": {
      "dispatcher": "orchestrator/dispatcher.md",
      "aggregator": "orchestrator/aggregator.md"
    }
  },
  "subAgents": [
    {
      "agentType": "conversationAgent",
      "enabled": true,
      "promptPath": "agents/conversation/instructions.md",
      "config": { "indexName": "...", "knowledgeAgentName": "..." }
    },
    {
      "agentType": "formSupportAgent",
      "enabled": true,
      "promptPath": "agents/formsupport/step0-Bot.md",
      "config": { "formDefinitionContainer": "...", "steps": ["..."] }
    }
  ]
}
```

### Import via Azure Data Explorer (Portal)

1. Open the Cosmos DB account in the Azure Portal.
2. Navigate to **Data Explorer → AgentMemoryDB → ClientProfiles**.
3. Click **Upload Item**.
4. Upload each JSON object from `client_profiles.json` individually (the Portal expects single documents, not arrays).

Alternatively, paste each document directly using **New Item** in Data Explorer.

### Import via Python SDK (seed script)

For local development or automated seeding, use the provided seed script:

```bash
# Ensure the Cosmos emulator (or Azure account) is reachable, then:
cd agentic_ai_backend/agents/orchestrators
python scripts/seed_cosmos.py
```

The script connects to the Cosmos emulator at `https://localhost:8081` using the well-known emulator master key, creates the database and container if they don't exist, and upserts each profile from `client_profiles.json`.

For seeding against a real Azure account, set the following environment variables before running:

```bash
export AZURE_COSMOS_DB_ENDPOINT="https://cosmos-nr-ai-form-dev.documents.azure.com:443/"
export AZURE_COSMOS_DB_KEY="<your-account-key>"
export AZURE_COSMOS_DB_DATABASE_NAME="AgentMemoryDB"
```

Then modify the script or run equivalent SDK code to upsert documents into the remote account.

---

## 5. RBAC Role Assignment (Managed Identity)

In production, the Container App's Managed Identity needs read access to Cosmos DB. Assign the **Cosmos DB Built-in Data Reader** role:

```bash
#!/usr/bin/env bash
# Assign Cosmos DB Built-in Data Reader role to Container App Managed Identity

RESOURCE_GROUP="rg-nr-ai-form-dev"
ACCOUNT_NAME="cosmos-nr-ai-form-dev"

# Get the Cosmos DB account resource ID
COSMOS_ACCOUNT_ID=$(az cosmosdb show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACCOUNT_NAME" \
  --query "id" --output tsv)

# Get the Container App Managed Identity principal ID
# Replace <container-app-name> with your actual Container App name
PRINCIPAL_ID=$(az containerapp identity show \
  --resource-group "$RESOURCE_GROUP" \
  --name "<container-app-name>" \
  --query "principalId" --output tsv)

# The built-in Cosmos DB Data Reader role definition ID
# This is a well-known GUID for "Cosmos DB Built-in Data Reader"
ROLE_DEFINITION_ID="00000000-0000-0000-0000-000000000001"

# Assign the role at account scope
az cosmosdb sql role assignment create \
  --resource-group "$RESOURCE_GROUP" \
  --account-name "$ACCOUNT_NAME" \
  --role-definition-id "$ROLE_DEFINITION_ID" \
  --principal-id "$PRINCIPAL_ID" \
  --scope "$COSMOS_ACCOUNT_ID"

echo "Cosmos DB Built-in Data Reader role assigned to Managed Identity."
```

> **Important:** The `Cosmos DB Built-in Data Reader` role is a Cosmos DB data-plane role (not an Azure RBAC role). It must be assigned using `az cosmosdb sql role assignment create`, not `az role assignment create`.

### Verifying the Assignment

```bash
az cosmosdb sql role assignment list \
  --resource-group "$RESOURCE_GROUP" \
  --account-name "$ACCOUNT_NAME"
```

---

## 6. Local Cosmos Emulator Setup (docker-compose)

The project's `docker-compose.yaml` (in `agentic_ai_backend/`) already includes the Cosmos emulator service:

```yaml
azure-cosmos-emulator:
  image: mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator
  platform: linux/amd64
  container_name: azure-cosmos-emulator
  ports:
    - "8081:8081"
    - "10250-10255:10250-10255"
  environment:
    - AZURE_COSMOS_EMULATOR_PARTITION_COUNT=3
    - AZURE_COSMOS_EMULATOR_ENABLE_DATA_PERSISTENCE=true
    - AZURE_COSMOS_EMULATOR_IP_ADDRESS_OVERRIDE=127.0.0.1
  volumes:
    - cosmosdb-data:/tmp
```

### Key Details

| Setting | Value | Purpose |
|---------|-------|---------|
| Port | `8081` | Emulator HTTPS endpoint |
| Ports | `10250-10255` | Direct connectivity ports |
| Partition Count | `3` | Supports multiple partition key values |
| Data Persistence | `true` | Data survives container restarts |
| IP Override | `127.0.0.1` | Allows `localhost` access |
| Volume | `cosmosdb-data:/tmp` | Persistent storage on host |

### Well-Known Emulator Master Key

```
C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==
```

This is a fixed, publicly documented key for the Cosmos emulator. It is not a secret.

### Emulator Connection String

```
AccountEndpoint=https://localhost:8081/;AccountKey=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==
```

### Quick Start (Local Development)

```bash
# 1. Start the Cosmos emulator
cd agentic_ai_backend
docker-compose up azure-cosmos-emulator -d

# 2. Wait for the emulator to be ready (check https://localhost:8081/_explorer/index.html)
#    The emulator takes 30-60 seconds to initialise on first run.

# 3. Seed the database with tenant profiles
cd agents/orchestrators
python scripts/seed_cosmos.py

# 4. Verify — open the emulator Data Explorer in your browser:
#    https://localhost:8081/_explorer/index.html
#    You should see AgentMemoryDB → ClientProfiles with 3 documents.
```

### Environment Variables for Local Development

Set the following in your orchestrator `.env` file:

```
AZURE_COSMOS_DB_ENDPOINT=https://localhost:8081
AZURE_COSMOS_DB_KEY=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==
AZURE_COSMOS_DB_DATABASE_NAME=AgentMemoryDB
CSSAI_EXECUTION_ENV=localhost
```

Setting `CSSAI_EXECUTION_ENV=localhost` disables TLS certificate verification so the application can connect to the emulator's self-signed certificate.

---

## Troubleshooting

### Emulator won't start

- Ensure Docker is running and has sufficient memory (the emulator needs ~2 GB).
- On Apple Silicon (M1/M2), the `platform: linux/amd64` flag enables Rosetta emulation. Performance may be slower.

### Connection refused on port 8081

- The emulator takes 30-60 seconds to initialise. Wait and retry.
- Check `docker logs azure-cosmos-emulator` for errors.

### SSL/TLS errors

- Ensure `CSSAI_EXECUTION_ENV=localhost` is set so the application disables certificate verification.
- For the seed script, TLS verification is already disabled (`connection_verify=False`).

### Data not persisting across restarts

- Verify the `cosmosdb-data` volume exists: `docker volume ls | grep cosmosdb-data`.
- Ensure `AZURE_COSMOS_EMULATOR_ENABLE_DATA_PERSISTENCE=true` is set in the compose file.


---

## Credential Chain Explained

The factory (`clientprofiles/factory.py`) resolves credentials in priority order. Only the first available credential is used:

### Priority 1: Account Key (`AZURE_COSMOS_DB_KEY`)

The key + endpoint as separate values. Works for both the local Cosmos emulator and remote Azure Cosmos DB accounts (any non-Managed-Identity environment).

```
AZURE_COSMOS_DB_ENDPOINT=https://localhost:8081/
AZURE_COSMOS_DB_KEY=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==
```

Or for a real Azure account:

```
AZURE_COSMOS_DB_ENDPOINT=https://your-account.documents.azure.com:443/
AZURE_COSMOS_DB_KEY=your-primary-key-from-portal
```

### Priority 2: DefaultAzureCredential (Managed Identity)

Used in any Azure-hosted environment (dev, test, production) when no key is set. The endpoint is still required (to know WHERE to connect), but authentication is handled automatically by Azure.

```
AZURE_COSMOS_DB_ENDPOINT=https://your-account.documents.azure.com:443/
# Do NOT set AZURE_COSMOS_DB_KEY
```

`DefaultAzureCredential` automatically authenticates using (in order):
1. Environment variables (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`)
2. Managed Identity (Container Apps, App Service, VMs with identity assigned)
3. Azure CLI login (`az login` on developer machines)
4. Visual Studio Code Azure extension

In production on Azure Container Apps:
- The Container App has a system-assigned Managed Identity
- The Cosmos DB account has a `Cosmos DB Built-in Data Reader` role assigned to that identity
- No secrets are stored anywhere - Azure handles auth automatically
- This same pattern works for dev and test environments hosted on Azure

For local development:
- Set `AZURE_COSMOS_DB_KEY` in your `.env` with the emulator key or a real key
- Set `CSSAI_EXECUTION_ENV=localhost` to disable TLS verification for the emulator

---

## Integration: How a WebSocket API Calls `resolve(client_id)`

The client profile store is designed to be called early in the request lifecycle — before the orchestrator dispatches work to sub-agents. Here's how a WebSocket (or HTTP) endpoint integrates with `resolve()`.

### Call Flow

```
Frontend (WebSocket client)
    │
    │  connects with client_id in query param or first message
    ▼
WebSocket/HTTP Endpoint (orchestrator_agent_server.py)
    │
    │  extracts client_id from request
    ▼
get_client_profile_store().resolve(client_id)
    │
    │  returns ClientProfile (or raises exception)
    ▼
Use profile data to configure orchestrator behavior
    │
    │  e.g. which sub-agents to enable, prompt paths, CORS, etc.
    ▼
orchestrate_a2a(query, ..., profile=profile)
```

### Integration Steps

#### 1. Accept `client_id` in the API contract

The frontend must send a `client_id` with each request. Options:

- **WebSocket**: as a query parameter on the connection URL  
  `ws://localhost:8002/ws?client_id=11111111-1111-4111-8111-111111111111`
- **HTTP POST** (`/invoke`): as a field in the JSON body  
  `{ "query": "...", "client_id": "11111111-..." }`

#### 2. Call `resolve()` in the endpoint handler

```python
from clientprofiles import get_client_profile_store, ClientIdRequiredError, ClientProfileNotFoundError

# Inside your WebSocket or HTTP handler:
store = get_client_profile_store()

try:
    profile = await store.resolve(client_id)
except ClientIdRequiredError:
    # 400 — client_id was missing or empty
    return error_response("client_id is required")
except ClientProfileNotFoundError:
    # 404 — no tenant profile exists for this client_id
    return error_response(f"Unknown client_id: {client_id}")
```

#### 3. Use the resolved profile

The `ClientProfile` gives you tenant-specific configuration:

```python
# profile.subAgents — which sub-agents are enabled for this tenant
# profile.tenantResources — blob paths, prompt paths, etc.
# profile.corsOrigins — allowed CORS origins for this tenant
# profile.orchestratorPrompts — dispatcher/aggregator prompt paths

# Example: pass to orchestrator
output = await orchestrate_a2a(
    query=request.query,
    conversation_agent_url=conversation_url,
    form_support_agent_url=form_support_url,
    step_number=step_number,
    session_id=session_id,
    # NEW: pass resolved profile for tenant-aware behavior
    # client_profile=profile
)
```

### WebSocket Example (FastAPI)

```python
from fastapi import WebSocket, WebSocketDisconnect, Query
from clientprofiles import get_client_profile_store, ClientIdRequiredError, ClientProfileNotFoundError

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str = Query(...)):
    store = get_client_profile_store()

    # Resolve tenant profile before accepting the connection
    try:
        profile = await store.resolve(client_id)
    except ClientIdRequiredError:
        await websocket.close(code=4000, reason="client_id is required")
        return
    except ClientProfileNotFoundError:
        await websocket.close(code=4004, reason=f"Unknown client_id: {client_id}")
        return

    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            # Use profile to configure orchestrator behavior per-tenant
            result = await orchestrate_a2a(
                query=data["query"],
                # ... other params ...
            )
            await websocket.send_json(result)
    except WebSocketDisconnect:
        pass
```

### HTTP `/invoke` Example (current pattern)

```python
@app.post("/invoke", response_model=InvokeResponse)
async def invoke_agent(request: InvokeRequest):
    store = get_client_profile_store()

    try:
        profile = await store.resolve(request.client_id)
    except ClientIdRequiredError:
        raise HTTPException(status_code=400, detail="client_id is required")
    except ClientProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown client_id: {request.client_id}")

    # Use profile for tenant-aware orchestration
    output = await orchestrate_a2a(
        query=request.query,
        conversation_agent_url=conversation_url,
        form_support_agent_url=form_support_url,
        step_number=request.step_number,
        session_id=request.session_id,
    )
    return InvokeResponse(response=output, session_id=request.session_id)
```

### Key Points

- `get_client_profile_store()` is a singleton — it creates the Cosmos connection once and reuses it. Safe to call on every request.
- `resolve()` does a point read (1 RU cost) — very fast, no query overhead.
- Call `resolve()` **before** accepting WebSocket connections so you can reject unknown tenants immediately with an appropriate close code.
- The `client_id` is a GUID that identifies the tenant — the frontend must know and send it.
