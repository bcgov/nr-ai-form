# Client Profiles — Setup Guide

## What This Does

Resolves per-tenant configuration from Cosmos DB using a `client_id`. Each tenant gets its own sub-agents, prompt paths, CORS origins, etc.

---

## Credentials

The factory picks the first available credential:

1. **`AZURE_COSMOS_DB_KEY`** — endpoint + key (local emulator, or any env without Managed Identity)
2. **`DefaultAzureCredential`** — Managed Identity (any Azure-hosted env: dev, test, prod)

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_COSMOS_DB_ENDPOINT` | Yes | Cosmos DB endpoint URL |
| `AZURE_COSMOS_DB_KEY` | No | Account key (if not set, uses Managed Identity) |
| `AZURE_COSMOS_DB_DATABASE_NAME` | No | Defaults to `AgentMemoryDB` |
| `CSSAI_EXECUTION_ENV` | No | Set to `localhost` to disable TLS verification |

Container name (`ClientProfiles`) is hardcoded in the factory.

---

## Local Development (Emulator)

```bash
# 1. Start emulator
docker-compose up -d

# 2. Seed data
cd agentic_ai_backend/agents/orchestrators
.venv/Scripts/python scripts/seed_local_emulator.py

# 3. Test
.venv/Scripts/python scripts/test_resolve.py
```

`.env` for local:
```
AZURE_COSMOS_DB_ENDPOINT=https://localhost:8081/
AZURE_COSMOS_DB_KEY=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==
AZURE_COSMOS_DB_DATABASE_NAME=AgentMemoryDB
CSSAI_EXECUTION_ENV=localhost
```

---

## Azure (Dev/Test/Prod)

Set `AZURE_COSMOS_DB_ENDPOINT` on the Container App. Don't set `AZURE_COSMOS_DB_KEY` — the app uses Managed Identity automatically.

Requires RBAC role assignment: `Cosmos DB Built-in Data Reader` on the Container App's managed identity.

---

## How to Call `resolve()` from WebSocket/HTTP

```python
from clientprofiles import get_client_profile_store

store = get_client_profile_store()
profile = await store.resolve(client_id)  # returns ClientProfile or raises exception
```

Raises `ClientIdRequiredError` (400) if `client_id` is missing, `ClientProfileNotFoundError` (404) if not found.

The returned `profile` contains: `subAgents`, `tenantResources`, `corsOrigins`, `orchestratorPrompts`.

---

## Seeding Data

| Script | Target | When to use |
|--------|--------|-------------|
| `scripts/seed_local_emulator.py` | Local emulator | After `docker-compose up` |
| `scripts/seed_azure_cosmos.py` | Real Azure account | One-time setup (needs endpoint + key) |

Seed data lives in `clientprofiles/seed/client_profiles.json`.

The `id` field is not required in the JSON — the seed scripts automatically set `id = clientId` for each document. If `clientId` is also missing, a random UUID is generated.

---

## Known Issues

1. **Emulator data persistence is broken.** The Cosmos DB Emulator has a known issue where data is lost when the emulator is stopped, even with `AZURE_COSMOS_EMULATOR_ENABLE_DATA_PERSISTENCE=true` configured. The seed script must be rerun after every emulator restart. Reference: [Azure/azure-cosmos-db-emulator-docker#96](https://github.com/Azure/azure-cosmos-db-emulator-docker/issues/96)

2. **Azure Cosmos DB seeding requires VNet access.** For real Azure Cosmos DB, the seed script must be executed from within the VM/VNet environment because access is restricted by Cosmos DB firewall rules. External machines (including CI/CD runners) cannot reach the endpoint directly.

---

## Docker Compose (Emulator)

```yaml
azure-cosmos-emulator:
  image: mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator
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

> **Note:** Data persistence on the Linux emulator is unreliable across `docker-compose down`/`up`. Use `docker-compose stop`/`start` to preserve data, or re-seed after each `up`.
