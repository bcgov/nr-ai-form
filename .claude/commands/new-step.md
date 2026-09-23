---
description: Scaffold a new form step for the FormSupportAgent (form definition JSON + prompt template Markdown + stepmappers entry).
---

Add a new step to the FormSupportAgent. Treat `$ARGUMENTS` as the step key in the form `stepN-Slug` (e.g. `step8-Review`). If `$ARGUMENTS` is empty, ask for the step key.

Steps:
1. Validate the key matches `^step\d+(-[A-Za-z0-9]+)+$`. If not, stop and ask for a corrected key.
2. Verify these files do **not** already exist (if any do, stop and report which):
   - `agentic_ai_backend/agents/formsupportagent/formdefinitions/<KEY>.json`
   - `agentic_ai_backend/agents/formsupportagent/prompttemplates/<KEY>.md`
3. Create the JSON form definition by copying the structure of an existing similar step (look at `step2-Eligibility.json` as a baseline). Leave field IDs and labels as TODO placeholders.
4. Create the prompt template by copying `step2-Eligibility.md` and clearly marking the parts that need to be customized.
5. Add a constant to `ai_bot_frontend/stepmappers.js` following the existing naming convention (`STEP<N>_<SLUG_UPPER>: "<KEY>"`).
6. Add an entry to `agentic_ai_backend/agents/orchestrators/workflowcomponents/formstepsintendmapper.json` with placeholder `shortDescription` and `intentTags`.
7. Print a punch list of what the user must fill in before the step is functional.

Do NOT commit the changes — leave them for the user to review.
