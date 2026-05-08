# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

The repo contains **two distinct backend stacks** plus a vanilla-JS frontend and Terraform/Terragrunt infra. The two backends are not alternative implementations of the same thing — they are different generations and currently coexist:

- `backend/` — first-generation monolith. This is an obsolete code folder. **Python 3.11**, FastAPI + LangGraph + LangChain, single process. Form-filling agents (`analyze_form_agent`, `process_field_agent`) drive a LangGraph `StateGraph` with `MemorySaver` checkpointing. Endpoints: `/api/process`, `/api/form/chat`. Entry: `backend/main.py`.
- `agentic_ai_backend/` — current multi-agent architecture. **Python 3.13**, Microsoft Agent Framework (`agent-framework-core`), three FastAPI services that talk to each other over the **A2A protocol** (HTTP/JSON). This is where active development happens (recent SHOWCASE-4287 commits). Entry points are the three `*_a2a_server.py` / `*_agent_server.py` files.
- `ai_bot_frontend/` — vanilla JS embed (`client.js`, `services.js`, `stepmappers.js`, `guided-questions/`). Calls the orchestrator at `http://localhost:8002/invoke`.
- `infra/`, `terragrunt/`, `scripts/`, `.github/workflows/` — Azure deployment (App Service **or** Azure Container Apps, switched by `deployment_type` Terraform variable). Workflows: `deploy-aca-{dev,test}.yml`, `deploy-to-{dev,test}.yml`.

When asked to change "the backend," confirm which one — they share no code.

## agentic_ai_backend architecture (read this before editing it)

Three independent FastAPI services live under `agentic_ai_backend/agents/`, each with its own `pyproject.toml`, `Dockerfile`, and `uv.lock`:

| Service | Port | Path | Role |
|---|---|---|---|
| `conversationagent` | 8000 | `agents/conversationagent/` | Q&A backed by Azure AI Search (tool: `tools/azure_ai_search.py`) |
| `formsupportagent` | 8001 | `agents/formsupportagent/` | Step-aware form field guidance; loads per-step JSON form definitions and Markdown prompt templates; has livestock water-consumption MCP tools |
| `orchestrators` | 8002 | `agents/orchestrators/` | Public entry point. Routes user queries to the two agents and curates a single response |

**Request flow** (`orchestrate_a2a` in `orchestrators/orchestratoragent.py`):

```
POST /invoke ─▶ Dispatcher ─fan-out─▶ ConversationAgentA2AExecutor ─┐
                  │                                                 ├─fan-in─▶ Aggregator ─▶ yield_output
                  └─ LLM intent classifier              FormSupportAgentA2AExecutor ─┘
```

- **Dispatcher** (`workflowcomponents/dispatcher.py`) — calls Azure OpenAI with structured output (`IntentListModel`) to pick `ConversationAgentA2A`, `FormSupportAgentA2A`, or both, with confidence 0–10. Falls back to keyword matching if Azure creds are missing. Strips `step<N>-Name:` prefixes from the query before classification. Loads `formstepsintendmapper.json` for form-step intent tags.
- **Executors** receive `IntentListModel`. Each calls `routing.get_intent_for_agent(task, self.id)`; if the intent has confidence < 7 (`HIGH_CONFIDENCE_THRESHOLD` in `routing.py`) **and is not the highest-confidence one for that agent**, the executor emits `{"skipped": true, ...}` instead of calling the remote agent. The Aggregator filters these out.
- **Aggregator** (`workflowcomponents/aggregator.py`) — calls Azure OpenAI again to merge the two responses into a single user-facing message. Has hardcoded behavioral rules in its system/user prompt (e.g. preserve Markdown links, never wrap radios as JSON, special-case Water Sustainability Act questions). Edit the prompt there, not in agent code.
- The workflow is wrapped as an agent (`workflow.as_agent`) so multi-turn state works. Session state is persisted to Redis via `threadmanagement/redisdbutils.py` (`AgentSession.from_dict` / `to_dict`). Cosmos DB equivalent exists (`cosmosdbutils.py`) but Redis is the default.

**Step identifier convention.** The orchestrator prepends `{step_number}:` to the user's query (e.g. `step2-Eligibility:Am I eligible?`) before passing it in. Both the dispatcher and `formsupportagent.extract_step_from_query` re-parse this prefix. Form definitions live in `formsupportagent/formdefinitions/<step>.json` and prompt templates in `formsupportagent/prompttemplates/<step>.md`; these can also be fetched from Azure Blob Storage when `AZURE_BLOBSTORAGE_CONNECTIONSTRING` and `AZURE_BLOBSTORAGE_CONTAINER` are set (see `services/formdefinitionservice.py`, `services/prompttemplateservice.py`). Step keys are enumerated in `ai_bot_frontend/stepmappers.js`.

**Shared `utils` package.** `agentic_ai_backend/utils/` is consumed by the three agent services via local path source in their `pyproject.toml`:

```toml
[tool.uv.sources]
utils = { path = "../../utils" }
```

`conversationagent` does **not** depend on `utils` — only `formsupportagent` and `orchestrators` do. When adding a new agent service, mirror this pattern.

## Common commands

### agentic_ai_backend (per-service, Python 3.13, `uv`)

Each agent service is a separate `uv` project. From its directory:

```powershell
uv sync                                 # install deps
uv run python conversationagent.py "your query"          # one-shot dryrun (conversationagent)
uv run python formsupportagent.py "step2-Eligibility:Am I eligible?"  # one-shot dryrun (formsupportagent)
uv run python orchestratoragent.py "your query"          # one-shot dryrun (orchestrators)
uv run python conversation_agent_a2a_server.py           # start FastAPI server (port 8000)
uv run python formsupport_agent_a2a_server.py            # start FastAPI server (port 8001)
uv run python orchestrator_agent_server.py               # start FastAPI server (port 8002)
```

Run the full stack (with Redis + Cosmos emulator) from `agentic_ai_backend/`:

```powershell
docker-compose up
```

The orchestrator's Dockerfile builds with context `agentic_ai_backend/` (it needs `utils/` as a sibling); the conversationagent's Dockerfile builds with context `agentic_ai_backend/agents/` (no utils). Don't change build contexts without updating both `docker-compose.yaml` and the Dockerfiles together.

Tests (orchestrators and formsupportagent each have a `tests/` dir):

```powershell
uv run pytest                                    # all tests in current service
uv run pytest tests/test_workflow_graph.py       # single file
uv run pytest tests/test_workflow_graph.py::TestRouting::test_select_subagents  # single test
```

### backend (Python 3.11, `uv`)

From `backend/`:

```powershell
uv sync
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000   # run from repo root, NOT from backend/
uv run pytest
uv run pytest --cov=backend --cov-report=html
```

Note the import path: `backend.main:app` is rooted at the repo root (`PYTHONPATH=/app` in the Dockerfile). Running `uvicorn main:app` from inside `backend/` will fail because internal imports use `from backend.x import y`. The `.vscode/tasks.json` "Run Backend Server" task uses `${workspaceFolder}` (repo root) as `cwd` — follow that pattern.

## Environment variables

`.env` files are gitignored and live alongside each service. Templates: `backend/env.example`, and `dev.env` / `test.env` files in each `agentic_ai_backend/agents/*` directory (these are committed but **contain real-looking credentials** — treat them as templates, do not commit changes that add new secrets).

Cross-cutting variables every service in `agentic_ai_backend/` reads:
- `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME`, `AZURE_OPENAI_API_VERSION`

Orchestrator-specific:
- `CONVERSATION_AGENT_A2A_URL` (default `http://localhost:8000`), `FORM_SUPPORT_AGENT_A2A_URL` (default `http://localhost:8001`)
- `FORM_STEP_NUMBER` (default `step2-Eligibility`)
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_SSL`, `REDIS_TTL_DAYS` — Redis is required for multi-turn sessions
- `CORS_ALLOW_ORIGINS` — comma-separated, used at startup

ConversationAgent-specific:
- `AZURE_SEARCH_API_KEY`, `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_INDEX_NAME`

FormSupportAgent-specific (optional, enables blob-store form definitions and prompt templates):
- `AZURE_BLOBSTORAGE_CONNECTIONSTRING`, `AZURE_BLOBSTORAGE_CONTAINER`

`backend/` reads `AZURE_OPENAI_DEPLOYMENT_NAME` (note: **without** `_CHAT_`) — different name from `agentic_ai_backend/`.

## Conventions to preserve

- **Azure-gateway compatibility shim.** Both `conversationagent.py` and `formsupportagent.py` define `AzureGatewayChatCompletionClient(OpenAIChatCompletionClient)` that injects a space into empty assistant content when `tool_calls` are present. The internal Azure gateway rejects null content there. Don't remove this without testing against the real gateway. The alias `AzureOpenAIChatClient = AzureGatewayChatCompletionClient` exists for older patches.
- **Confidence threshold = 7** is duplicated as a constant in `workflowcomponents/routing.py`. Search for `HIGH_CONFIDENCE_THRESHOLD` if tuning routing.
- **The aggregator's prompt is the product surface.** A lot of UX behavior (e.g. how livestock calculations are displayed, BCEID button guidance, Water Sustainability Act answers) lives in the aggregator's user prompt rather than in agent code or templates. Look there before assuming a bug is in an agent.
- **Tests reference deferred sub-agents.** Workflow tests use `StubDispatcher`/`StubWorker` to feed `IntentListModel` directly — copy that pattern instead of mocking HTTP clients when adding tests under `orchestrators/tests/`.

## Deployment

Two GitHub Actions deployment paths via Terraform `deployment_type` variable:
- App Service: `deploy-to-dev.yml`, `deploy-to-test.yml`
- Azure Container Apps: `deploy-aca-dev.yml`, `deploy-aca-test.yml`

`scripts/setup-github-actions-oidc.sh` provisions the OIDC managed identity and Terraform state storage. See `docs/DEPLOYMENT_GUIDE.md` and `docs/CONTAINER_APPS_NETWORKING.md` for the long-form playbook.
