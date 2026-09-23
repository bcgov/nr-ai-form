---
description: Run `uv sync` in every agent service under agentic_ai_backend so all uv projects are aligned with their lockfiles.
---

The `agentic_ai_backend/` tree contains four independent `uv` projects (each with its own `pyproject.toml` and `uv.lock`) that need to be synced separately. Run `uv sync` in each of these directories, in this order, reporting any failures:

1. `agentic_ai_backend/utils/` — shared package (path-sourced by the others)
2. `agentic_ai_backend/agents/conversationagent/`
3. `agentic_ai_backend/agents/formsupportagent/`
4. `agentic_ai_backend/agents/orchestrators/`

If `$ARGUMENTS` is `--include-backend`, also run `uv sync` in `backend/` (the legacy Python 3.11 monolith).

Use parallel Bash calls when there are no ordering dependencies (everything after `utils/` can run in parallel). Report a one-line summary per directory: ok / failed-with-reason.
