---
description: Send a query to the running orchestrator at http://localhost:8002/invoke and pretty-print the response.
---

POST the user's query to the local orchestrator and report the curated response.

Steps:
1. Treat `$ARGUMENTS` as the query text. If empty, ask the user what to send.
2. Build the JSON body. Default `step_number` to `step2-Eligibility` unless the query already contains a `stepN-...:` prefix or the user specifies one in `$ARGUMENTS` (e.g. `step3-Add-Surface-Water-Source: <query>`). Generate a fresh `session_id` (UUID) unless the user provides one.
3. POST to `http://localhost:8002/invoke` with `Content-Type: application/json`.
4. Print: the request body, the HTTP status, the aggregated `response` field, and the `thread_id` returned in the result. If the response contains `original_results`, show them collapsed with one line per source.

If the orchestrator is not running (connection refused), suggest `/run-stack` and stop.
