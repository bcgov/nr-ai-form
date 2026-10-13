---
description: Start the full agentic_ai_backend stack (orchestrator + 2 agents + Redis + Cosmos emulator) via docker-compose.
---

Start the local stack defined in `agentic_ai_backend/docker-compose.yaml`. Services:

- `conversation-agent` (port 8000)
- `formsupport-agent` (port 8001)
- `orchestrator-agent` (port 8002)
- `redis` (port 6379)

Steps:
1. Verify the per-service `.env` files exist (`agentic_ai_backend/agents/{conversationagent,formsupportagent,orchestrators}/.env`). If any are missing, list them and stop — do not start the stack with missing env files.
2. From `agentic_ai_backend/`, run `docker-compose up -d` (or `docker-compose up` if `$ARGUMENTS` contains `--foreground`).
3. After ~10 seconds, hit `GET http://localhost:8002/health` and report the orchestrator's status. If it fails, also report `docker-compose ps` and the last 20 lines of `docker-compose logs orchestrator-agent`.

Confirm with the user before running `docker-compose down` or rebuilding images.
