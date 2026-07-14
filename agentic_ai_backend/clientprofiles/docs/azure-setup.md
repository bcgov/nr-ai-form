# Client Profiles - Setup Guide

## What This Does

Resolves per-tenant configuration from Cosmos DB using a `client_id`. Each tenant gets its own sub-agents, prompt paths, CORS origins, etc.

---

## Credentials

The factory picks the first available credential:

1. **`AZURE_COSMOS_DB_KEY`** - endpoint + key (local emulator, or any env without Managed Identity)
2. **`DefaultAzureCredential`** - Managed Identity (any Azure-hosted env: dev, test, prod)

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_COSMOS_DB_ENDPOINT` | Yes | Cosmos DB endpoint URL |
| `AZURE_COSMOS_DB_KEY` | No | Account key (if not set, uses Managed Identity) |
| `AZURE_COSMOS_DB_DATABASE_NAME` | No | Defaults to `AgentMemoryDB` |
| `CSSAI_EXECUTION_ENV` | No | Set to `localhost` to disable TLS verification |

Container name (`ClientProfiles`) is hardcoded in the factory.

---

## Environment Configuration by Deployment

| Environment | `AZURE_COSMOS_DB_ENDPOINT` | `AZURE_COSMOS_DB_KEY` | `CSSAI_EXECUTION_ENV` | Auth Method |
|-------------|---------------------------|----------------------|----------------------|-------------|
| Local (venv outside Docker) | `https://localhost:8081` | Emulator master key | `localhost` | Key |
| Local (docker-compose) | `https://azure-cosmos-emulator:8081` | Emulator master key | `localhost` | Key |
| Dev (Azure Container Apps) | `https://<account>.documents.azure.com:443/` | *(do not set)* | *(do not set)* | Managed Identity |
| Test (Azure Container Apps) | `https://<account>.documents.azure.com:443/` | *(do not set)* | *(do not set)* | Managed Identity |
| Prod (Azure Container Apps) | `https://<account>.documents.azure.com:443/` | *(do not set)* | *(do not set)* | Managed Identity |

**Key rules:**
- `CSSAI_EXECUTION_ENV=localhost` disables TLS cert verification (required for emulator's self-signed cert). Never set this in Azure.
- `AZURE_COSMOS_DB_KEY` is only set for the local emulator. In Azure, omitting it makes the factory use `DefaultAzureCredential` (Managed Identity).
- Inside docker-compose, use the Docker service name `azure-cosmos-emulator` (not `localhost`) because containers resolve DNS by service name.

---

## Local Development (Emulator)

Before running the runtime services with `docker-compose up`, create the local `.env` files from `.sampleenv` and replace placeholder values with actual development values. For local seeding, `scripts/seed_local_emulator.py` uses the Cosmos emulator endpoint/key defaults; the `cosmos-seed` container overrides only `COSMOS_EMULATOR_ENDPOINT` and `SEED_FILE_PATH`.

Also review `clientprofiles/seed/client_profiles.json` before seeding. Cosmos profiles should contain tenant config such as deployment names, prompt paths, search indexes, and knowledge agent names, but not raw API keys, OpenAI endpoints, storage connection strings, or blob container names. Set `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_SEARCH_API_KEY`, `AZURE_SEARCH_ENDPOINT`, `AZURE_BLOBSTORAGE_CONNECTIONSTRING`, and `AZURE_BLOBSTORAGE_CONTAINER` in the relevant service `.env` files before running the services. The Docker `cosmos-seed` service only needs the Cosmos emulator endpoint and seed JSON. The orchestrator reads `agents/orchestrators/.env`, the conversation agent reads `agents/conversationagent/.env`, and the form support agent reads `agents/formsupportagent/.env` when those services start.

Do not commit real keys, OpenAI endpoints, storage connection strings, or blob container names after replacing placeholders for local testing.

**Option A: Running orchestrator outside Docker (venv)**

```bash
# 1. Start emulator
docker-compose up azure-cosmos-emulator -d

# 2. Seed data (or rely on cosmos-seed container)
cd agentic_ai_backend/agents/orchestrators
.venv/Scripts/python scripts/seed_local_emulator.py

# 3. Test
.venv/Scripts/python scripts/test_resolve.py
```

`.env` for local venv:
```
AZURE_COSMOS_DB_ENDPOINT=https://localhost:8081/
AZURE_COSMOS_DB_KEY=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==
AZURE_COSMOS_DB_DATABASE_NAME=AgentMemoryDB
CSSAI_EXECUTION_ENV=localhost
```

**Option B: Running full stack via docker-compose**

```bash
docker-compose up
```

The `cosmos-seed` service waits for the emulator to become ready, then seeds automatically. The orchestrator container's environment is already configured in `docker-compose.yaml` to point at `https://azure-cosmos-emulator:8081`.

---

## Azure (Dev/Test/Prod)

Set only `AZURE_COSMOS_DB_ENDPOINT` on the Container App environment. Example:

```
AZURE_COSMOS_DB_ENDPOINT=https://nraif-671b-dev-cosmos.documents.azure.com:443/
```

Do NOT set `AZURE_COSMOS_DB_KEY` or `CSSAI_EXECUTION_ENV`. The app uses Managed Identity automatically with standard TLS.

Requires RBAC role assignment: `Cosmos DB Built-in Data Reader` on the Container App's managed identity.

---

## How to Resolve Tenant Config from WebSocket/HTTP

Production route handlers should use `TenantConfigService`, not `store.resolve()` directly:

```python
from clientprofiles import TenantConfigService, get_client_profile_store

service = TenantConfigService(get_client_profile_store())
tenant_config = await service.get_config(client_id)
profile = tenant_config.profile          # CORS/origin metadata
settings = tenant_config.settings        # validated per-agent settings
fingerprint = tenant_config.fingerprint  # safe cache version
```

`TenantConfigService` keeps a process-local fresh TTL cache and a longer stale fallback window. It resolves Cosmos once per tenant per fresh TTL, converts the `ClientProfile` into typed settings, validates required fields, and computes a short config fingerprint for cache keys.

Raises `ClientIdRequiredError` (400) if `client_id` is missing, `ClientProfileNotFoundError` (404) if not found, `TenantConfigInvalidError` (500) if the Cosmos document is missing required runtime settings, and `TenantConfigUnavailableError` (503) if Cosmos is temporarily unavailable and no stale cache is usable.

---

## Runtime Request Flow

Production HTTP traffic should use tenant-scoped routes so the tenant is known before CORS preflight. Browser WebSocket traffic can use the API gateway plain `/ws` route when the first message includes `client_id`:

```text
POST /tenants/{client_id}/invoke
WS   /ws
```

The orchestrator resolves `TenantConfig` at the HTTP/WebSocket boundary. The workflow receives `TenantAgentSettings`, not the raw Cosmos document. Sub-agent settings are converted to dictionaries only at the final A2A request boundary because the current sub-agent invoke contracts are JSON payloads. Deployment-owned values such as OpenAI/Search API keys, OpenAI endpoint, blob connection string, and blob container name are read from service environment variables and are not included in the forwarded `client_settings` payload.

Direct sub-agent invocation (`conversationagent /invoke` or `formsupportagent /invoke`) bypasses Cosmos resolution, so callers must include the full `client_settings` object in the request body. This is intended for local testing and diagnostics; production clients should call the orchestrator so tenant settings are resolved and validated centrally.

For normal orchestrator traffic, `configFingerprint` is generated from the Cosmos tenant profile by `build_config_fingerprint(profile)`. For direct sub-agent testing, callers may use any stable non-secret string such as `"local-test"`; changing it intentionally bypasses existing prompt/agent cache entries.

The API gateway exposes `WS /ws` for browser-facing WebSocket proxying without tenant id in the URL. The first message must include `client_id`; the gateway resolves that tenant, validates `Origin`, and opens a downstream connection to the orchestrator plain `/ws` route with `client_id` in the JSON payload.

Browser-facing session ids should stay tenant-neutral, for example `session-abc123`. The orchestrator converts that public id into an internal backend key shaped as `{client_id}:{session_id}` before calling the workflow. Redis and sub-agent memory use the internal key so two tenants cannot collide if they send the same browser session id. The internal key should not be returned to the frontend.

---

## Tenant Settings Shape

`ClientProfile` remains the Cosmos document shape. At runtime it is converted into typed settings with `build_tenant_agent_settings(profile)` inside `TenantConfigService`:

- `ConversationAgentSettings` for the conversation agent.
- `FormSupportAgentSettings` for the form support agent.
- `OrchestratorPromptSettings` for dispatcher and aggregator prompt paths.

Required values fail fast during tenant config resolution, before the workflow or sub-agents run. Each sub-agent settings payload includes `clientId` and `configFingerprint` so downstream caches can be keyed safely without raw secrets.

---

## Runtime Caches

All caches are process-local and short TTL. Use distributed cache/session storage later if multiple replicas need shared state.

| Cache | Key shape | Default TTL |
|-------|-----------|-------------|
| Tenant config | `client_id` | `TENANT_PROFILE_FRESH_TTL_SECONDS=300` |
| Stale tenant fallback | `client_id` | `TENANT_PROFILE_STALE_TTL_SECONDS=86400` |
| Orchestrator prompts | `configFingerprint + container + prompt path + file` | `ORCHESTRATOR_PROMPT_CACHE_TTL_SECONDS=300` |
| Form definitions | `clientId + configFingerprint + folder + file` | `FORM_SUPPORT_ASSET_CACHE_TTL_SECONDS=300` |
| Form step prompts | `clientId + configFingerprint + folder + file` | `FORM_SUPPORT_ASSET_CACHE_TTL_SECONDS=300` |
| FormSupportAgent instances | `clientId + configFingerprint + step_id` | `FORM_SUPPORT_AGENT_CACHE_TTL_SECONDS=300` |
| Common agent prompts | `clientId + configFingerprint + promptPath` | `FORM_SUPPORT_PROMPT_CACHE_TTL_SECONDS=300`, `CONVERSATION_PROMPT_CACHE_TTL_SECONDS=300` |

Cache keys never include blob connection strings, API keys, or full tenant settings. The fingerprint changes when the tenant profile changes, which naturally invalidates old generated assets and agents.

---

## CORS and WebSocket Origin Rules
Tenant profiles should list exact origins, for example:

```json
"corsOrigins": ["https://test.j200.gov.bc.ca"]
```

Paths are ignored because browser `Origin` headers never include paths. Local development may use `http://localhost*`, which matches localhost with any port but does not match lookalike hosts such as `http://localhost.evil`. Do not use `*` in tenant profiles.

---

## Secret Handling

Do not commit real account keys, search API keys, OpenAI endpoints, storage connection strings, or blob container names in seed files. These deployment-owned values are resolved from environment variables (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_SEARCH_API_KEY`, `AZURE_SEARCH_ENDPOINT`, `AZURE_BLOBSTORAGE_CONNECTIONSTRING`, `AZURE_BLOBSTORAGE_CONTAINER`) at runtime and are intentionally kept out of Cosmos and forwarded `client_settings`. Production should later move these environment values to Key Vault references or managed identity wherever the downstream SDK supports it. Debug logs should still avoid dumping full request payloads, but `client_settings` should no longer contain these deployment-owned secrets.

### TODO: Externalize Tenant Secrets

Tenant secrets and deployment-owned endpoints have been moved out of Cosmos DB and are currently resolved from deployment environment variables. Follow-up work should move those environment values to Key Vault references or managed identity wherever SDK support exists, while preserving the current fail-fast validation behavior.

---

## Seeding Data

| Script | Target | When to use |
|--------|--------|-------------|
| `scripts/seed_local_emulator.py` | Local emulator | After `docker-compose up` |
| `scripts/seed_azure_cosmos.py` | Real Azure account | One-time setup (needs endpoint + key) |

Seed data lives in `clientprofiles/seed/client_profiles.json`.

The `id` field is not required in the JSON - the seed scripts automatically set `id = clientId` for each document. If `clientId` is also missing, a random UUID is generated.

Seed profiles are validated before upsert using the current strict runtime schema. Each seeded tenant must include the supported `conversationAgent` and `formSupportAgent` entries, their required config values, and the required `tenantResources.config` orchestrator runtime values. Missing required values stop the seed script before any Cosmos upsert.

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
  volumes:
    - cosmosdb-data:/tmp
```

> **Note:** Data persistence on the Linux emulator is unreliable across `docker-compose down`/`up`. Use `docker-compose stop`/`start` to preserve data, or re-seed after each `up`.
