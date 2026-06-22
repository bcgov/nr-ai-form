# OpenShift build manifests — agentic_ai_backend

One Template per agent, each bundling that agent's **ImageStream + BuildConfig**,
to build the three agent images into the OpenShift **`1dca6b-tools`** project
(the BCGov "tools" namespace used for builds).

| Template file              | ImageStream / BuildConfig | Dockerfile (relative to `contextDir`)   | Port |
|----------------------------|---------------------------|------------------------------------------|------|
| `orchestrator-agent.yaml`  | `orchestrator-agent`      | `agents/orchestrators/Dockerfile`        | 8002 |
| `conversation-agent.yaml`  | `conversation-agent`      | `agents/conversationagent/Dockerfile`    | 8000 |
| `formsupport-agent.yaml`   | `formsupport-agent`       | `agents/formsupportagent/Dockerfile`     | 8001 |

## Build context

All three Dockerfiles `COPY utils/` and `agents/...`, so the Docker build
context must be the `agentic_ai_backend/` directory — exactly the `context: .`
used in `docker-compose.yaml`. The BuildConfigs reflect this with:

- `source.contextDir: agentic_ai_backend`
- `strategy.dockerStrategy.dockerfilePath:` the per-agent path **relative to that contextDir**

## Apply

Each file is an OpenShift **Template**, applied with `oc process | oc apply`.
Each creates both the ImageStream and the BuildConfig for that agent:

```bash
oc project 1dca6b-tools

oc process -f orchestrator-agent.yaml | oc apply -f -
oc process -f conversation-agent.yaml | oc apply -f -
oc process -f formsupport-agent.yaml  | oc apply -f -
```

Override parameters as needed (defaults shown in each template's `parameters:`):

```bash
oc process -f orchestrator-agent.yaml \
  -p NAMESPACE=1dca6b-tools \
  -p GIT_REF=master \
  | oc apply -f -
```

Each template takes the same parameters:

| Parameter   | Default |
|-------------|---------|
| `NAMESPACE` | `1dca6b-tools` |
| `GIT_URI`   | `https://github.com/bcgov/nr-ai-form.git` |
| `GIT_REF`   | `dev-AA-SHOWCASE-4381` |

## Trigger builds

These BuildConfigs use a **Git source**. Re-process with a different `GIT_REF`
to point at another branch/tag, then start a build:

```bash
oc start-build orchestrator-agent  -n 1dca6b-tools --follow
oc start-build conversation-agent  -n 1dca6b-tools --follow
oc start-build formsupport-agent   -n 1dca6b-tools --follow
```

### Build straight from your local working tree (no git push needed)

Add a binary source override on the fly — run from the `agentic_ai_backend/`
directory so the upload root matches `contextDir`:

```bash
cd agentic_ai_backend

oc start-build orchestrator-agent  -n 1dca6b-tools --from-dir=. --follow
oc start-build conversation-agent  -n 1dca6b-tools --from-dir=. --follow
oc start-build formsupport-agent   -n 1dca6b-tools --from-dir=. --follow
```

> When building `--from-dir=.` from inside `agentic_ai_backend/`, the upload root
> already is the build context, so the `contextDir: agentic_ai_backend` in the
> BuildConfig is ignored for that build and the `dockerfilePath` resolves against
> the uploaded root — which is correct.

## Resulting images

```
image-registry.openshift-image-registry.svc:5000/1dca6b-tools/orchestrator-agent:latest
image-registry.openshift-image-registry.svc:5000/1dca6b-tools/conversation-agent:latest
image-registry.openshift-image-registry.svc:5000/1dca6b-tools/formsupport-agent:latest
```

## Promote to dev / test (env tags)

Each build pushes to `:latest`. Add `:dev` / `:test` tags in the **same**
`1dca6b-tools` ImageStream to mark what's promoted to each environment, then
point the environment's Deployment at that tag. Run from the `1dca6b-tools`
project (`oc project 1dca6b-tools`):

```bash
# dev tags
oc tag orchestrator-agent:latest orchestrator-agent:dev
oc tag conversation-agent:latest conversation-agent:dev
oc tag formsupport-agent:latest  formsupport-agent:dev

# test tags
oc tag orchestrator-agent:latest orchestrator-agent:test
oc tag conversation-agent:latest conversation-agent:test
oc tag formsupport-agent:latest  formsupport-agent:test
```

> These point `:dev` / `:test` at whatever `:latest` resolves to **at tag time**.
> Re-run after a new build to re-point them. To pin an immutable image, tag from
> a specific build's digest instead.

Alternatively, promote into separate runtime namespaces by tagging across
namespaces:

```bash
oc tag 1dca6b-tools/orchestrator-agent:latest 1dca6b-dev/orchestrator-agent:latest
```

## Deploy to 1dca6b-test

Runtime manifests deploy the `:test` images from `1dca6b-tools` into the
**`1dca6b-test`** namespace. Each `*-deploy.yaml` is a Template bundling a
**Deployment + Service + Route** for one agent:

| Deploy template                   | Service / Route      | Container port | Image (`:test` tag) |
|-----------------------------------|----------------------|----------------|----------------------|
| `orchestrator-agent-deploy.yaml`  | `orchestrator-agent` | 8002           | `1dca6b-tools/orchestrator-agent:test` |
| `conversation-agent-deploy.yaml`  | `conversation-agent` | 8000           | `1dca6b-tools/conversation-agent:test` |
| `formsupport-agent-deploy.yaml`   | `formsupport-agent`  | 8001           | `1dca6b-tools/formsupport-agent:test`  |

The orchestrator Deployment overrides `CONVERSATION_AGENT_A2A_URL` and
`FORM_SUPPORT_AGENT_A2A_URL` to the in-cluster Service names
(`http://conversation-agent:8000`, `http://formsupport-agent:8001`).

### 1. Allow 1dca6b-test to pull images from 1dca6b-tools (one-time)

```bash
oc policy add-role-to-user system:image-puller \
  system:serviceaccount:1dca6b-test:default \
  -n 1dca6b-tools
```

### 2. Create the Secrets

Each agent's env is a `Secret` generated from its `.env`, kept in this folder as
`<agent>-secret.yaml` (gitignored — contains real credentials). Apply into
`1dca6b-test`:

```bash
oc apply -f conversation-agent-secret.yaml
oc apply -f formsupport-agent-secret.yaml
oc apply -f orchestrator-agent-secret.yaml
```

The Deployments load these via `envFrom.secretRef`
(`conversation-agent-env`, `formsupport-agent-env`, `orchestrator-agent-env`).

### 3. Deploy

```bash
oc project 1dca6b-test

oc process -f conversation-agent-deploy.yaml | oc apply -f -
oc process -f formsupport-agent-deploy.yaml  | oc apply -f -
oc process -f orchestrator-agent-deploy.yaml | oc apply -f -
```

Deploy-template parameters (same for all three):

| Parameter         | Default |
|-------------------|---------|
| `NAMESPACE`       | `1dca6b-test` |
| `IMAGE_REGISTRY`  | `image-registry.openshift-image-registry.svc:5000` |
| `IMAGE_NAMESPACE` | `1dca6b-tools` |
| `IMAGE_TAG`       | `test` |
| `REPLICAS`        | `1` |

Get the public URLs:

```bash
oc get route -n 1dca6b-test
```

> **Redis caveat:** the orchestrator Secret carries `REDIS_HOST=10.0.0.71`
> (an Azure private IP) from `.env`. Multi-turn sessions need a Redis reachable
> from the cluster — point `REDIS_HOST`/`REDIS_PORT` at an in-cluster Redis or a
> reachable managed instance before relying on session state.

These build manifests only produce images; all runtime config comes from the
Secrets above (see also the env-var section in the repo `CLAUDE.md`).
