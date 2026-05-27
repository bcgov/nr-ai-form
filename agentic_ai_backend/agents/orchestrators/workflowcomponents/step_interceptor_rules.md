# Step Interceptor Rules

This document describes how the orchestrator uses `workflowcomponents/step_interceptor_rules.json` to block sub-agent execution based on user query content.

## Purpose

The step interceptor lets the orchestrator return an immediate placeholder response before sending a query to the Conversation Agent or Form Support Agent.

This is useful for:
- Queries about legal/representation support that should not be routed to AI agents
- Redirecting users to an official contact channel like FrontCounter BC
- Preventing unsupported or out-of-scope assistant behavior for sensitive topics

## Rule format

Each rule in `step_interceptor_rules.json` is a standard JSON object with these fields:

- `id`: unique rule name
- `match_terms`: array of case-insensitive phrases to search for in the user query
- `skip_agents`: `true` means the orchestrator returns the rule response and does not call sub-agents
- `response_source`: metadata used in the returned payload, e.g. `Aggregator`
- `response`: text the orchestrator returns immediately when the rule matches

### Matching behavior

- `match_terms` are matched as case-insensitive substrings in the user query.
- The first rule with a matching term is returned.
- The orchestrator only intercepts when `skip_agents` is `true`.

## Adding more keywords

To add more trigger phrases, update the `match_terms` array in any rule.

### Example: add more keywords

```json
{
  "id": "out-of-scope-keywords",
  "match_terms": [
    "consultant",
    "lawyer",
    "notary",
    "representative",
    "authorization letter",
    "agent",
    "proxy",
    "your-new-keyword"
  ],
  "skip_agents": true,
  "response_source": "Aggregator",
  "response": "Please reframe your question or contact -FRONTCOUNTER-BC- for further assistance."
}
```

### Example: create a different rule

```json
{
  "id": "out-of-scope-keywords",
  "match_terms": [
    "keyword1",
    "keyword2"
  ],
  "skip_agents": true,
  "response_source": "Aggregator",
  "response": "I cannot assist with this topic. Please contact support for help."
}
```

## What if I want to allow normal agent routing?

If a topic should allow normal agent routing, do not add its keywords to the rules.

- No matching rule = no interception
- The orchestrator will continue to invoke the Conversation Agent and Form Support Agent as usual

### If no out-of-scope keywords are needed

You have two options:

**Option 1: Keep the file with an empty list**
```json
[]
```

**Option 2: Delete the file entirely**

Both approaches work the same way:
- `_load_step_interceptor_rules()` returns an empty list (either from file or on missing file)
- `find_step_interceptor()` finds no matches and returns `None`
- No errors or blocking occurs
- Normal agent routing proceeds

**Recommendation:** Keep the file with `[]` rather than deleting it, because:
- It's clearer to future maintainers that the feature exists but is disabled
- You won't break the orchestrator if the file goes missing accidentally
- Easy to re-enable later by just adding rules back to the array
