---
description: Run pytest across every test directory in agentic_ai_backend (orchestrators and formsupportagent currently have tests).
---

Run pytest in each agent service that has a `tests/` directory:

- `agentic_ai_backend/agents/orchestrators/` — uses `uv run pytest`
- `agentic_ai_backend/agents/formsupportagent/` — uses `uv run pytest`

If `$ARGUMENTS` is non-empty, pass it through to pytest (e.g. `/test-agents -k routing` or `/test-agents tests/test_workflow_graph.py::TestRouting`).

Run them in parallel via separate Bash calls. Summarize results as a table: service | passed | failed | skipped.

Do not include the legacy `backend/` directory unless the user asks.
