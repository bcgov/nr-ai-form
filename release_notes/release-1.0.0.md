# Release 1.0.0 — Agentic AI Backend and Water Tenant Client (Production)

First production release of the AI form assistant on Azure. It has two parts:

- **Backend.** The `agentic_ai_backend` multi-agent stack from this repo, running on Azure Container Apps (ACA). Production was **not rebuilt**: it runs the exact container images that were deployed and tested in TEST under tag `test-aca-97`. They were promoted by digest to `prod-aca-41`.
- **Client and tenants.** The `client.js` browser embed and the per-tenant agent assets (prompts, form definitions, step mapper) from [bcgov/ai-form-client](https://github.com/bcgov/ai-form-client), released as [Production Release 1.0.0](https://github.com/bcgov/ai-form-client/releases/tag/Release1) (tag `Release1`).

## Release at a glance

| Item | Value |
|---|---|
| Version | **1.0.0** |
| Environment | Production — Azure, Canada Central |
| Deployment type | Azure Container Apps (`deployment_type = "container_apps"`) |
| Resource group | `nr-ai-form-prod` |
| Release date | 2026-11-16 (backend apply finished 2026-11-17 00:04 UTC) |
| Promoted test image tag | **`test-aca-97`** |
| Production image tag | **`prod-aca-41`** (the rolling `prod` tag points at the same images) |
| Application code | `dev-commonservices` @ `234e066`, built by [Deploy ACA to Test #97](https://github.com/bcgov/nr-ai-form/actions/runs/42294145151) on 2026-11-06 |
| Infrastructure code | `master` @ `ac5ff5d` |
| Production pipeline | [Deploy ACA to Prod #41 — apply (test-aca-97)](https://github.com/bcgov/nr-ai-form/actions/runs/43983863144), preceded by plan run #40 |
| Terraform result | `Apply complete! Resources: 0 added, 2 changed, 0 destroyed.` |
| Client release | [bcgov/ai-form-client — Production Release 1.0.0](https://github.com/bcgov/ai-form-client/releases/tag/Release1), tag `Release1` → `ec1f780` |
| Tenant | Water (Water Permit App) |

## Backend: container images

Registry: `ghcr.io/bcgov/nr-ai-form`

| Image | Production tag | Manifest digest |
|---|---|---|
| `orchestrator_agent` | `prod-aca-41` | `sha256:8681c333c84644dd49ff517486c914ebb0017dbc7b02036a63f38b194e7fc776` |
| `conversation_agent` | `prod-aca-41` | `sha256:b804e83bdd0060b691b3b7ef40e7c69eb74ddfad6ff633bcff1d349341dde1c5` |
| `formsupport_agent` | `prod-aca-41` | `sha256:6ff042310c6b2bfef4522722cf7f2fa0b3757613ca58d8097547510be2dd822d` |
| `api_backend` | `prod-aca-41` | `sha256:489908de1a2bece9ed73e4079e7e43e36eb63afa9663c5370866023bfe187292` |

On 2026-11-25, `docker buildx imagetools inspect` showed that `test-aca-97`, `prod-aca-41` and `prod` resolve to the same digest for all four images.

## Backend: what's in this release

### Services (one Container App, four containers)

| Container | Role |
|---|---|
| `api_backend` | Public entry point, reached through Front Door. WebSocket gateway (`/ws`) that relays `client.js` sessions to the orchestrator. Also serves session history (`/tenants/{client_id}/history/{session_id}`) and `/health`. |
| `orchestrator_agent` (8002) | Dispatcher classifies intent with Azure OpenAI and sends the query to one or both sub-agents over A2A. The aggregator merges their answers into one response. Multi-turn session state is stored in Redis. |
| `conversation_agent` (8000) | Knowledge Q&A grounded in Azure AI Search. |
| `formsupport_agent` (8001) | Step-aware form-field guidance from per-step form definitions and prompt templates, plus tenant-selected in-process MCP calculation tools. |

### Capabilities

- **Intent routing.** The dispatcher picks `ConversationAgentA2A`, `FormSupportAgentA2A`, or both, with a confidence score from 0 to 10. A sub-agent is skipped when its intent scores below 7 and is not its highest-confidence intent.
- **Edge-case handling.** Seven out-of-scope categories get fixed templated answers, and no sub-agent is called: predicting outcomes, legal advice, personal legal matters, external record lookups, internal policy, out-of-scope subjects and unrelated topics.
- **Form guidance coverage for the water licence application.** Steps 0 to 10: Bot, Introduction, Eligibility, Technical Information (Add Purpose, Surface Water Source, Wells, Works, Joint Works, Dam/Reservoir, Water Diversion, Land Tenure, Other Authorizations, Project Information, Fee Exemption Request), Location, Document Upload, Privacy Confirmation, Applicant and Co-Applicant Information, Review, Declarations and Signatures, and Complete.
- **Tenant-specific configuration.** Each tenant has its own form-step intent mapper (`stepmapper.json`), agent prompts, form definitions and prompt templates in Azure Blob Storage, and its own MCP tool sets in its client profile.
- **Calculation tools.** A livestock water-consumption calculator for the Water tenant.

### Application changes since UAT (`UAT-AUGUST-2026`)

| Commit | Change |
|---|---|
| `c6cc28f` (#304) | Dispatcher skill prompt kept in sync with Azure |
| `28c98c9` (#306), `4acbb3e` (#307) | Prompt fixes for language and water diversion answers (conversation agent, form support agent, aggregator) |
| `dde2a02` (#309) | Water allocation notation, maximum rate of diversion, and question:answer query format fixes |
| `0993edd` (#308) | FormSupportAgent MCP tools are selected per tenant through `mcpTools` in the ClientProfile. |
| `4c8366c` (#308) | Orchestrator loads the intent stepmapper from Blob Storage, so stepmappers can differ per tenant |
| `2d25509` (#311) | Form definition and prompt template updates (Eligibility, Project Information, Works, Dam/Reservoir, multi-file upload) |
| `cf2a3e0` (#311) | `docker-compose` includes privoxy (local development only) |
| `881467f` (#314) | SHOWCASE-4629 / SHOWCASE-4616: new `personal_legal_matter` edge-case intent, and automation test updates |
| `234e066` (#312) | "Form Assist" renamed to "Application Assistant". Prompts and form definitions synced (Add Purpose, Fee Exemption Request, Eligibility, shared upload and address templates). |

## Client and Water tenant (`bcgov/ai-form-client`)

The client repo holds one folder per tenant under `src/tenant/<tenant>/`:

- `scripts/` contains `client.js` and its UI modules, which host web pages load.
- `assets/` contains the agent prompts, form definitions, prompt templates and step mapper, which the backend reads at runtime.

GitHub release [Production Release 1.0.0](https://github.com/bcgov/ai-form-client/releases/tag/Release1) is tag `Release1` on `main` @ `ec1f780` (PR #67, 2026-11-11). It was published on 2026-11-25.

### How tenants are deployed

- **Trigger.** A push to `main` that changes `src/tenant/<tenant>/**` runs that tenant's workflow (`deploy-water.yml` for Water). On `main` the workflow uses the `prod` GitHub environment; the `dev` and `test` branches deploy to their own environments.
- **Upload.** `deploy-tenant-reusable.yml` logs in to Azure with OIDC and runs `az storage blob sync` twice:
  - `src/tenant/<tenant>/scripts` goes to the static website container `$web`, under `scripts/tenants/<tenant>/`. Host pages load `client.js` from here. HTML test pages are not uploaded.
  - `src/tenant/<tenant>/assets` goes to the `assets` container, under `tenants/<tenant>/`. The backend finds these files through `tenantResources` in each PROD client profile (for example `tenants/water/stepmapper`).
- **No deletes.** The sync runs with `--delete-destination false`, so a file removed from Git stays in storage until someone removes it by hand.
- **RAG documents.** Source documents under `src/tenant/water/rag/` are kept in Git but are not deployed by these workflows.
- **Client profiles (backend side).** Profiles are managed in this repo at `agentic_ai_backend/clientprofiles/prod/clientprofiles.json`. During each backend prod apply, the `nraif-671b-prod-cp-sync` Container Apps Job upserts them into Cosmos DB (`AgentMemoryDB/ClientProfiles`). Terraform generates a stable GUID for each profile.

### Water tenant in this release

| Item | Value |
|---|---|
| PROD client profile | Water Permit App |
| PROD profile ID (Terraform output `client_profile_ids`) | `7a1c0271-557f-158f-2bb9-8921d1239e82` |
| MCP tool sets (PROD profile) | `LIVESTOCK_WATER_CONSUMPTION_TOOLS` |
| Chat model (PROD profile) | `gpt-5.1` |
| Assistant name in the UI | Application Assistant |
| Host origins allowed (PROD CORS) | `j200.gov.bc.ca`, `train.j200.gov.bc.ca`, `test.j200.gov.bc.ca`, `delivery.j200.gov.bc.ca`, `localhost` |
| Last PROD deploy | [Deploy Water Tenant #108](https://github.com/bcgov/ai-form-client/actions/runs/42927943018), 2026-11-11 00:00 UTC |
| Commit deployed | `ec1f780` (PR #67), the `Release1` tag |
| `client.js` backend (`API_BACKEND_BASE_URL`) | PROD Front Door: `https://nr-ai-form-prod-api-fd-bpf6chbhdhf6c5gd.a03.azurefd.net` |
| `client.js` `clientId` | `7a1c0271-557f-158f-2bb9-8921d1239e82`, which matches the PROD profile |
| Assets deployed to `tenants/water/` | Agent prompts (dispatcher, aggregator, conversation agent, form support agent, edge cases, graceful decline), 36 form definitions, 41 prompt templates, step mapper |

### client.js features

- **Connection.** Connects to `api_backend` over a WebSocket (`/ws`), and restores earlier conversations from `GET /tenants/{clientId}/history/{sessionId}`.
- **Form step.** Sends the current form step with each question. `stepmappers.js` maps the host page to a step key such as `step2-Eligibility`.
- **Application ID.** Reads the host application's `applicationId` from the page and keeps it in `sessionStorage`, so each application gets its own chat session.
- **UI.** Launcher, welcome panel, guided (suggested) questions, a header menu with expand/collapse and delete chat, a draggable and resizable pop-up, call-outs, a form overlay, and Markdown rendering of replies.

### Tenant changes in this release (`main`, since 2026-10-01)

**Water**

| Commit(s) | Change |
|---|---|
| `067b7d8`, `56ef3e5` | "Form Assist" renamed to "Application Assistant" |
| `b04faed`, `e008d6f`, `42ba1fa`, `62c9117`, `a1c088b` | Chatbot UI content and styling, pop-up resize improvements, reply formatting fix |
| `605ca71`, `9d176ea` | Canadian English spelling in the UI |
| `372e103`, `652b13e`, `5f4e010`, `3c524b2` | More concise replies and self-introduction; eligibility explanation and Add Purpose fixes |
| `ecbb667`, `1bd4809` | Eligibility bug fix; the bot no longer confuses users by suggesting a new water licence |
| `6a39e77`, `35df3a4`, `066888b`, `d76316e` | "How many purposes" handling for Step 3 Water Diversion, and Add Purpose instructions |
| `c88fe67` | SHOWCASE-4629 / 4616 / 4598: legal-matter handling, and no recommending a new application |
| `b9935df`, `cdd09c2` | SHOWCASE-4570: the Fee Exemption comment box is filled only when the user explicitly asks |
| `df3ac86`, `88d2463` | Form definitions and prompts synced with the backend |
| `1043cb9`, `48ccb03` | `client.js` pointed at the PROD Front Door and the PROD Water client ID |

**Shared and workflows**

| Commit(s) | Change |
|---|---|
| `a4a1141` | Per-tenant step mapper used by the backend for intent classification (pairs with backend `4c8366c`) |
| `2d0c86b`, `49220c7` | Tenant asset upload enabled in the deploy workflow |
| `3765bc6`, `049d6a3` | SHOWCASE-4682: tenant RAG documents stored in Git; the RAG upload workflow was later removed |

## Production infrastructure

Provisioned with Terraform/Terragrunt (`terragrunt/prod/terragrunt.hcl`) under SHOWCASE-4636, SHOWCASE-4637 and SHOWCASE-4705.

- **Azure Container Apps.** At least 1 replica is always running (no scale-to-zero). The default maximum is 10. Per-replica resources total 2.5 vCPU / 5 Gi:

  | Container | CPU | Memory |
  |---|---|---|
  | orchestrator_agent | 1 | 2Gi |
  | conversation_agent | 0.5 | 1Gi |
  | formsupport_agent | 0.5 | 1Gi |
  | api_backend | 0.5 | 1Gi |

- **Azure Front Door Premium with WAF.** Front Door reaches the Container App over Private Link. Public network access to the Container Apps environment is disabled, so clients must use the Front Door endpoint (`nr-ai-form-prod-api-fd`). The WAF rules were adjusted so the `session_id` query string is allowed through (SHOWCASE-4705).
- **Azure AI Search.** Provisioned with 1 replica. It reaches Blob Storage and Azure OpenAI through shared private links and authenticates with its managed identity.
- **Azure OpenAI.** A `text-embedding-3-large` deployment for the search index and knowledge base (GlobalStandard SKU).
- **Azure Managed Redis.** Stores multi-turn session state. Host, port and key are wired into the Container App from Terraform outputs.
- **Storage Account.** Tenant agent assets live in the `assets` blob container, under `tenants/<tenant>/`.
- **Cosmos DB.** Stores client profiles, synced from Git by the `nraif-671b-prod-cp-sync` job.
- **Health probes.** Startup, readiness and liveness probes on `/health` for every container, plus Front Door origin health probes.
- **Not provisioned in PROD:** Azure Document Intelligence.

## How the backend was deployed

Workflow: `.github/workflows/deploy-aca-prod.yml`, run manually with `test_tag = test-aca-97`.

1. **Plan (run #40).** Checked that all four `test-aca-97` images exist and ran `terragrunt plan`. Nothing was tagged or applied.
2. **Apply (run #41).** Gated by required reviewers on the `prod` GitHub environment.
   1. **Promote.** Added the `prod-aca-41` tag to the existing `test-aca-97` digests. This copies the manifest only; nothing is rebuilt.
   2. **Terragrunt apply.** Ran with `prevent_destroy: true`, which aborts if anything would be destroyed or replaced. Result: 0 added, 2 changed, 0 destroyed. The Container App images moved from `prod-aca-39` to `prod-aca-41`; both tags point at the same `test-aca-97` digests.
   3. **Tag prod.** Moved the rolling `prod` tag to the `prod-aca-41` images.

### Backend deployment history leading to 1.0.0

| Date (UTC) | Prod run | Test tag | Infra commit | Notes |
|---|---|---|---|---|
| 2026-10-30 to 2026-11-09 | #1–#33 | `test-aca-96` | various | Initial PROD provisioning and hardening: resource group, Redis, Search, OpenAI, Cosmos, Private Link and Front Door |
| 2026-11-10 | #36 | `test-aca-97` | `c18bf01` | First promotion of `test-aca-97`, with client profiles managed from Git |
| 2026-11-12 | #38 | `test-aca-97` | `ea97a60` | Front Door WAF fix for `session_id` |
| 2026-11-13 | #39 | `test-aca-97` | `074cc8b` | Client profile update |
| **2026-11-16** | **#41** | **`test-aca-97`** | **`ac5ff5d`** | **Release 1.0.0.** Per-container CPU and memory set from HCL. |

## Post-deployment verification

Check that the running Container App uses the promoted digests. This needs `docker login ghcr.io` and `az login` to the prod subscription:

```bash
./scripts/verify-prod-images.sh test-aca-97 prod-aca-41 nr-ai-form-prod
```

Status:

- GHCR digest check (`test-aca-97` = `prod-aca-41` = `prod`) passed on 2026-11-25.
- The running Container App check (the third argument) has not been recorded in this note yet.

## Rollback

**Backend.** Images are promoted by digest, so rolling back means promoting an earlier known-good test tag.

1. Run **Deploy ACA to Prod** with `test_tag = test-aca-96` and `command = plan`, then review the plan.
2. Run it again with `command = apply`. This needs approval on the `prod` environment.

This rolls back the container images only. Terraform and Terragrunt code always comes from the branch the workflow runs on, so an infrastructure change is reverted by reverting it on `master` and re-applying.

**Client and tenant assets.** Revert the commit on `main` in `bcgov/ai-form-client` and push. The tenant workflow re-uploads the previous file versions. Because the sync never deletes, any file the bad commit added must be removed from storage by hand.

## References

- Jira: SHOWCASE-4636 (prod provisioning), SHOWCASE-4637 (Front Door, Private Link, prod CI/CD), SHOWCASE-4705 (WAF and container resources), SHOWCASE-4629 / 4616 / 4598 (legal-matter handling), SHOWCASE-4570 (fee exemption comment), SHOWCASE-4682 (tenant RAG documents)
- Backend workflows: `.github/workflows/deploy-aca-test.yml`, `.github/workflows/deploy-aca-prod.yml`
- Backend prod config: `terragrunt/prod/terragrunt.hcl`, `agentic_ai_backend/clientprofiles/prod/clientprofiles.json`
- Client repo: [bcgov/ai-form-client](https://github.com/bcgov/ai-form-client). Workflows `deploy-water.yml`, `deploy-tenant-reusable.yml`.
- Guides: `docs/DEPLOYMENT_GUIDE.md`, `docs/CONTAINER_APPS_NETWORKING.md`, `agentic_ai_backend/clientprofiles/docs/azure-setup.md`

## Sign-off

| Role | Name | Date |
|---|---|---|
| Deployed by | | 2026-11-16 |
| Prod environment approver | | |
| QA / UAT sign-off | | |
