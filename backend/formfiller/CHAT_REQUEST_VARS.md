# Chat request variables — developer reference

This document describes the chat request variables used by the Form Filler agentic AI flow in `app/formfiller`.
It explains expected types, purpose, example payloads, common edge cases, and implementation notes for developers working on the agents and graph.

The variables appear as keys in the runtime `FormFillerState` object passed through the LangGraph StateGraph. The agent nodes read and update this state.

---

## Variables (summary)

- `user_message` (str) — The free-text message typed by the user in the AI assistance form.
- `form_fields` (list[dict]) — The canonical representation of the form or current page's fields (server/fetch + user edits).
- `filled_fields` (list[dict]) — Fields that the agent has successfully filled/confirmed.
- `missing_fields` (list[str|dict]) — The list of fields still required by the agent (IDs or dicts with `data_id`).
- `current_field` (Optional[dict|list[dict]]) — The single field the agent is actively working on (frontend uses this to highlight).
- `conversation_history` (list[dict]) — Chat history for the session: list of `{role: "user"|"assistant"|"system", content: str}`.
- `status` (Literal["in_progress","awaiting_info","completed"]) — Current flow status.
- `response_message` (str) — Short assistant message intended for the UI (what the agent expects next or the answer summary).
- `thread_id` (str) — Unique ID for the conversation/thread (future memory/reference).

---

## Detailed descriptions and intended use

### `user_message`
- Type: string
- Purpose: The user's current natural-language instruction or answer typed into the assistant form.
- Where it comes from: Frontend input box (the AI assistance text field).
- How agents use it: To drive intent detection, RAG searches, or to provide the content the LLM should use to fill form fields.

Notes for devs:
- Validate (in most cases) that this is a non-empty string before invoking RAG or LLM calls.
- Normalize whitespace, trim, and optionally limit to a max length before sending to LLMs.

Example:
```json
{"user_message": "I need to apply for the water permit. My land parcel number is 123-456 and my company is ACME Ltd."}
```

---

### `form_fields`
- Type: list[dict]
- Purpose: The authoritative model of the form at the time of the request. This should reflect the latest server data, user selections, and any prior AI updates.
- Typical keys in each field dict (project-specific):
  - `data_id` / `field_id` — stable identifier for the field
  - `fieldLabel` — human label
  - `fieldType` — `input`, `select`, `radio`, `checkbox`, `textarea`, etc.
  - `fieldValue` — current value (may be `""` or `None`)
  - `is_required` or `required` — boolean
  - `options` — list of strings for selects/radios
  - `validation_message` — string used to indicate constraints
  - `description` — help text

Intended use:
- If `form_fields` is present and non-empty, the orchestrator should route to `analyze_form` which attempts to map `user_message` to the existing fields.
- UI should merge edits from the user (in-page interactions) into this payload before calling the agent.

Important:
- Keep `form_fields` up-to-date. Agents rely on `fieldValue` to detect which fields are already filled.
- For long multi-page forms, `form_fields` may contain the whole form or only visible page fields depending on your design; be consistent.

Example (single field):
```json
{
  "data_id": "owner_name",
  "fieldLabel": "Owner name",
  "fieldType": "input",
  "fieldValue": "",
  "is_required": true,
  "validation_message": "Please provide a full name"
}
```

---

### `filled_fields`
- Type: list[dict]
- Purpose: Keep a record of fields the agent has produced values for (or confirmed). This is distinct from `form_fields` which is the canonical form state.
- Behavior:
  - Agents append to `filled_fields` when they successfully extract or produce a value for a field.
  - The orchestrator or caller can merge `filled_fields` back into `form_fields` for the final payload sent to servers.
  - For multi-page flows, `filled_fields` should correspond to the payload that will be submitted for the current agent iteration — avoid accumulating across unrelated sessions unless intended.

Example:
```json
[
  {"data_id": "owner_name", "fieldValue": "ACME Ltd"},
  {"data_id": "parcel_number", "fieldValue": "123-456"}
]
```

Developer notes: ??
- Use `data_id` to dedupe when appending. The graph code already dedupes by `data_id` before appending.
- Consider storing `confidence` or `source` (e.g., `ai`, `user`, `server`) if you need provenance.

Frontend session note:
- Because the current implementation stores session or transient data in the frontend, every request payload must include the latest full form state (all `form_fields`, `filled_fields`, etc.).
- This means the frontend must send the complete payload on each call so the backend has the canonical view of the current session. You can remove this requirement once session management is moved to the backend (persistent session store keyed by `thread_id`).
- Implementation tip: on the frontend, after the AI agent updates the HTML form with values from `filled_fields`, the frontend should merge those values into `form_fields` and then clear (empty) `filled_fields` from the payload before the next user-initiated request. This prevents duplicate submissions and keeps the payload minimal.

---

### `missing_fields`
- Type: list[str] or list[dict] (mixed allowed)
- Purpose: Tracks fields the agent has identified as required but not yet filled. Used to drive follow-up prompts, human-in-the-loop, or UI highlighting.
- Behavior:
  - Produced by `analyze_form` (or by the LLM analysis) when mapping `user_message` to the `form_fields`.
  - May contain string IDs or dicts that include e.g. `data_id` and `reason` keys.

Example:
```json
["owner_name", {"data_id":"parcel_number", "reason":"format required"}]
```

Developer notes:
- The code expects `missing_fields` to accept both strings and dicts. When removing items, compare by `data_id` or the string value.

---

### `current_field`
- Type: Optional[dict] or Optional[list[dict]]
- Purpose: The one field the agent is actively working on. The frontend uses this to set the form focus / highlight and display validation text.
- Behavior:
  - At any time only one `current_field` should be the prime focus (the graph code uses the first element if given a list).
  - `current_field` should include `validation_message` so the agent can surface constraints to the user.

Example:
```json
{"data_id":"owner_name", "fieldLabel":"Owner name", "validation_message":"Please include first and last name"}
```

Developer notes:
- Keep this small. Use it for immediate human prompts and validation only.
- When the agent fills the `current_field`, remove it from `missing_fields` and append it to `filled_fields`.

---

### `conversation_history`
- Type: list[dict]
- Purpose: Persistent convo history for the current thread. Elements have `{role, content}` structure.
- Where used: optionally provided to the LLM for context, RAG, or follow-up clarifications.

Example:
```json
[
  {"role":"user", "content":"I am applying for a permit..."},
  {"role":"assistant", "content":"Which permit type?"}
]
```

Developer notes:
- The graph currently appends a system-level summary (see `add_history_summary`) when appropriate.
- Be mindful of token budget if you pass the entire history to an LLM.

---

### `status`
- Type: Literal["in_progress","awaiting_info","completed"]
- Purpose: Flow state machine status used by `route_next_step` to determine graph progression.

Meaning:
- `in_progress` – Flow is running normally and more work may be done.
- `awaiting_info` – Agent requires input (either from user or another agent) to proceed.
- `completed` – Flow has finished for the current invocation.

Developer notes:
- Agents should set `status` to `completed` when they have produced a final response and no further routing is needed.
- The orchestrator uses `form_fields` presence to decide where to route; `status` controls graph termination or human-in-loop routing.

---

### `response_message`
- Type: string
- Purpose: Friendly text for the UI; what the agent expects next or a short answer summary.

Developer notes:
- Keep concise. Use `conversation_history` for longer context if needed.

---

### `thread_id`
- Type: string
- Purpose: Thread identifier for the conversation; used later for memory/long-term storage.

Developer notes:
- Generate with a uuid4 on a new session. Persist if you plan to attach memory or later resume the session.

---

## Example full `FormFillerState` payload
```json
{
  "user_message": "Please fill in my contact and parcel info",
  "form_fields": [
    {"data_id":"owner_name","fieldLabel":"Owner name","fieldType":"input","fieldValue":"","is_required":true},
    {"data_id":"parcel_number","fieldLabel":"Parcel number","fieldType":"input","fieldValue":"","is_required":true}
  ],
  "filled_fields": [],
  "missing_fields": ["owner_name","parcel_number"],
  "current_field": null,
  "conversation_history": [],
  "status": "in_progress",
  "response_message": "",
  "thread_id": "0a1b2c3d-..."
}
```

---

## JSON schema (minimal) — for quick validation
```json
{
  "type": "object",
  "properties": {
    "user_message": {"type":"string"},
    "form_fields": {"type":"array"},
    "filled_fields": {"type":"array"},
    "missing_fields": {"type":"array"},
    "current_field": {},
    "conversation_history": {"type":"array"},
    "status": {"type":"string", "enum":["in_progress","awaiting_info","completed"]},
    "response_message": {"type":"string"},
    "thread_id": {"type":"string"}
  }
}
```

---

## Developer guidance, edge cases, and best practices

1. Validation & sanitization
   - Validate `form_fields` shape on entry. Ensure `data_id` exists for fields that will be referenced.
   - Trim and sanitize `user_message` before sending to RAG/LLM.

2. Dedupe and idempotency
   - When appending to `filled_fields`, dedupe by `data_id`.
   - Avoid duplicate `conversation_history` entries — the graph implementation attempts to prevent duplicate system summaries.

3. Token and privacy management
   - Minimize sending the entire `conversation_history` to LLMs. Generate a short summary (the graph adds one) or send the last N messages.
   - Redact PII if your LLM provider requires it.

4. Multi-page flows
   - Decide whether `form_fields` carries the entire multi-page form or only the visible page. Be explicit in the API contract.
   - For large forms prefer sending just the companion context and the page fields to avoid token overages.

5. Human-in-loop
   - When `status == "awaiting_info"`, the frontend may pause and prompt the user. Use `current_field` + `response_message` to drive the UI.

6. RAG / search
   - The `search_tool` can be used to enrich LLM prompts (RAG). Tune the prompt to include the search results and the `user_message`.

7. Threading and memory
   - Use `thread_id` for future long-term memory. Persist `filled_fields` with the thread as a key for resume.

8. Tests
   - Add unit tests for `analyze_form`, `process_field_input`, and the orchestrator node.
   - Include tests for mixed `missing_fields` (strings and dicts) and for dedupe logic.

---

## Suggested next steps notes
- Add a small unit test that runs `chat_analyze_form` with:
  - only `user_message` (should route to the query/explain flow), and
  - with `form_fields` present (should route to `analyze_form`).
- Add more explicit types (Pydantic models) if you need runtime validation.
- Consider adding provenance metadata like `confidence`, `source`, and timestamps to `filled_fields`.

---