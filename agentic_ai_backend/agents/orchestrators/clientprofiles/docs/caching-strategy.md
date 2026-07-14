# Caching Strategy

**TTL = Time To Live** — how long a cached value is kept in memory before it is
considered expired and the next request triggers a fresh load from the source.

This document describes every caching layer in the agentic backend, what is cached,
the default TTLs, and the env vars that control them.

## Overview

There are four caching layers across the orchestrator and sub-agents. All caches are
**time-based** — they have no awareness of blob or Cosmos changes. Updating a prompt
template in Azure Blob Storage or a client profile in Cosmos DB will **not** take effect
until the relevant TTL expires.

```
Request
  └── Orchestrator: TenantConfigService  (Cosmos DB client profile)
        └── FormSupportAgent A2A Server: _agent_cache  (built agent per step)
              └── FormSupportAgent: _COMMON_INSTRUCTIONS_CACHE  (common instructions blob)
        └── ConversationAgent: _INSTRUCTIONS_CACHE  (instructions blob, LLM mode only)
```

---

## Layer 1 — Orchestrator: TenantConfigService

**File:** `tenantconfigservice.py` → delegates to `clientprofiles.TenantConfigService`

**What is cached:** The full `TenantConfig` object per `client_id`. This includes:
- The `ClientProfile` document read from Cosmos DB
- The parsed and validated `TenantAgentSettings` (tenant OpenAI deployment config, search config, prompt paths, CORS origins, etc.)
- The `config_fingerprint` used as a cache key downstream

**Two-tier design (fresh + stale):**

| Tier | Behaviour | Default | Env var |
|---|---|---|---|
| Fresh | Served from memory, no Cosmos read | 300 seconds | `TENANT_PROFILE_FRESH_TTL_SECONDS` |
| Stale | Used if Cosmos read fails (outage/timeout) | 86400 seconds (24 hours) | `TENANT_PROFILE_STALE_TTL_SECONDS` |
| Lookup timeout | Max wait for a Cosmos read before falling back to stale | 0.5 seconds | `TENANT_PROFILE_LOOKUP_TIMEOUT_SECONDS` |

**Implications:**
- Updating a client profile in Cosmos takes up to 5 minutes to propagate (fresh TTL).
- During a Cosmos outage, known tenants continue to work for up to 24 hours.
- Unknown tenants (no stale entry) always fail closed — there is no fallback for new
  tenants during an outage.
- The cache is process-local. Each orchestrator replica has its own independent cache.

---

## Layer 2 — Form Support A2A Server: Agent Cache

**File:** `formsupport_agent_a2a_server.py` (`_agent_cache`)

**What is cached:** A fully initialised `FormSupportAgent` instance per
`(client_id, config_fingerprint, step_key)`. Building an agent involves:
1. Reading the form definition JSON from Azure Blob Storage
2. Reading the step prompt template (`.md`) from Azure Blob Storage
3. Reading the common instructions blob from Azure Blob Storage
4. Assembling the full instruction string
5. Constructing the Azure OpenAI client and agent object

Caching this avoids 3 blob reads and the client construction on every request.

| Setting | Default | Env var |
|---|---|---|
| TTL | 300 seconds | `FORM_SUPPORT_AGENT_CACHE_TTL_SECONDS` |

**Set to `0` to disable** caching entirely (every request rebuilds from blob). Useful
during active prompt development so changes take effect immediately. Set to a higher
value (e.g. `600`) in production when prompts are stable.

**Cache key:** `(client_id, config_fingerprint, step_key)`
- Different tenants → different entries
- Different steps (`step2-Eligibility`, `step3-AddPurpose`, etc.) → different entries
- Config change in Cosmos (new fingerprint) → old entry is abandoned, new entry created

**Eviction:** Expired entries are evicted lazily on each cache miss to prevent
unbounded memory growth.

---

## Layer 3 — FormSupportAgent: Common Instructions Cache

**File:** `formsupportagent.py` (`_COMMON_INSTRUCTIONS_CACHE`)

**What is cached:** The raw text of the common instructions blob (shared rules appended
to all form support prompts). This is loaded once per `(client_id, fingerprint, blob_path)`
and reused for the TTL window.

| Setting | Default | Env var |
|---|---|---|
| TTL | 300 seconds | `FORM_SUPPORT_PROMPT_CACHE_TTL_SECONDS` |

Note: This cache is also hit during `FormSupportAgent.__init__()`, which itself runs
inside Layer 2's agent cache miss path. In practice, if Layer 2 is enabled, Layer 3 is
only reached once per agent TTL window.

---

## Layer 4 — ConversationAgent: Instructions Cache

**File:** `conversationagent.py` (`_INSTRUCTIONS_CACHE`)

**What is cached:** The raw instruction text loaded from Azure Blob Storage for the
conversation agent (LLM mode only — knowledgebase mode does not use instructions).

| Setting | Default | Env var |
|---|---|---|
| TTL | 300 seconds | `CONVERSATION_PROMPT_CACHE_TTL_SECONDS` |

**Note:** The `ConversationAgent` does **not** cache the agent or client object itself —
it constructs a new OpenAI client on every request. This is a known gap compared to
the `FormSupportAgent` pattern, which caches the full agent. For production at scale,
the `ConversationAgent` should be refactored to also cache the built agent per tenant.

---

## Summary Table

| Cache | Location | What | Key | Default TTL | Env var |
|---|---|---|---|---|---|
| Tenant config | Orchestrator | Cosmos profile + parsed settings | `client_id` | 300s fresh / 24h stale | `TENANT_PROFILE_FRESH_TTL_SECONDS` / `TENANT_PROFILE_STALE_TTL_SECONDS` |
| Form agent | Form support A2A server | Built `FormSupportAgent` | `(client_id, fingerprint, step_key)` | 300s | `FORM_SUPPORT_AGENT_CACHE_TTL_SECONDS` |
| Form common instructions | `formsupportagent.py` | Common instructions blob text | `(client_id, fingerprint, blob_path)` | 300s | `FORM_SUPPORT_PROMPT_CACHE_TTL_SECONDS` |
| Conversation instructions | `conversationagent.py` | Instructions blob text (LLM mode) | `(client_id, fingerprint, prompt_path)` | 300s | `CONVERSATION_PROMPT_CACHE_TTL_SECONDS` |

---

## When Do Changes Take Effect?

| Change | Which cache | How long until live |
|---|---|---|
| Update client profile in Cosmos | Layer 1 | Up to 5 min (fresh TTL) |
| Update prompt template blob | Layer 2 + 3 | Up to 5 min (agent TTL) |
| Update conversation instructions blob | Layer 4 | Up to 5 min |
| Update common form instructions blob | Layer 3 | Up to 5 min (or agent TTL if Layer 2 active) |

To force immediate pickup of a change without restarting the service, set
`FORM_SUPPORT_AGENT_CACHE_TTL_SECONDS=0` before deploying the update, then restore
after confirming.

---

## Development vs Production

| Env | Recommended TTL | Rationale |
|---|---|---|
| Local development | `FORM_SUPPORT_AGENT_CACHE_TTL_SECONDS=0` | Prompt changes take effect immediately |
| Staging / testing | Default (300s) | Matches production behaviour |
| Production | Default (300s) or higher | Minimises blob reads under load |

---


## TTL Location Recommendation

Keep cache TTLs as service/deployment environment variables rather than tenant profile fields in Cosmos DB. TTLs control process-local operational behavior, not tenant business configuration. This is especially important for `TENANT_PROFILE_FRESH_TTL_SECONDS`: reading the tenant profile from Cosmos to learn how long to cache that same profile creates a circular dependency. Use Cosmos for tenant-specific config and env vars for cache policy. Set a TTL to `0` to disable that cache layer entirely during active prompt/config development.
## Environment Variable Reference by Agent

Each agent has its own `.sampleenv` file. The TTL env vars are scoped to the agent that uses them.

### `agents/orchestrators/.sampleenv`

| Env var | Default | Description |
|---|---|---|
| `TENANT_PROFILE_FRESH_TTL_SECONDS` | `300` | How long Cosmos DB tenant profiles are served from memory before re-reading |
| `TENANT_PROFILE_STALE_TTL_SECONDS` | `86400` | How long stale profiles are used if Cosmos is unavailable (outage fallback) |
| `TENANT_PROFILE_LOOKUP_TIMEOUT_SECONDS` | `0.5` | Max wait for a Cosmos read before falling back to stale cache |
| `ORCHESTRATOR_PROMPT_CACHE_TTL_SECONDS` | `300` | How long dispatcher/aggregator prompt blobs are cached |

### `agents/formsupportagent/.sampleenv`

| Env var | Default | Description |
|---|---|---|
| `FORM_SUPPORT_AGENT_CACHE_TTL_SECONDS` | `300` | How long the fully-built `FormSupportAgent` (blob reads + OpenAI client) is cached per (tenant, step). Set to `0` during prompt development |
| `FORM_SUPPORT_PROMPT_CACHE_TTL_SECONDS` | `300` | How long the common instructions blob text is cached independently |
| `FORM_SUPPORT_ASSET_CACHE_TTL_SECONDS` | `300` | How long form definitions and step prompt templates loaded from blob are cached |

### `agents/conversationagent/.sampleenv`

| Env var | Default | Description |
|---|---|---|
| `CONVERSATION_PROMPT_CACHE_TTL_SECONDS` | `300` | How long the conversation instructions blob text is cached (LLM mode only) |
