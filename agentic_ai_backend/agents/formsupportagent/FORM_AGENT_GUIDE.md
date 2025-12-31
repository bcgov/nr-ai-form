# Form Support Agent - Technical Guide

This document outlines the enhanced dynamic prompting system for the `FormSupportAgent`. The agent is now designed to dynamically switch its persona, specialized knowledge, and instruction set based on the specific form field it is assisting with.

## Core Features
- **Dynamic Prompting**: Automatically loads a specialized `.md` prompt template based on the current form step.
- **Skill Markdown**: Uses structured Markdown (Role, Goal, Instructions) for high-precision AI reasoning.
- **Asset Separation**: Keeps form schemas (`.json`) separate from AI instructions (`.md`).
- **A2A Ready**: Exposes a FastAPI server for Agent-to-Agent communication.

---

## Directory Structure
The agent relies on two main folders inside `agentic_ai_backend/agents/formsupportagent/`:

1.  **`formdefinitions/`**: Contains the JSON schemas for each step (e.g., `step3-Add-Well.json`).
2.  **`prompttemplates/`**: Contains the Skill Markdown instructions (e.g., `step3-Add-Well.md`).

> **Note**: For every step, there must be a matching `.md` file in the templates folder.

---

## How to Run Locally (using `uv`)

The agent can be run directly from the terminal for testing purposes.

### Command Format
```bash
uv run formsupportagent.py "<step-identifier>: <your-query>"
```

### Examples

#### 1. Well Technical Info
```bash
uv run formsupportagent.py "step3-Add-Well: my hole in the ground is 50ft deep"
```

#### 2. Eligibility Check
```bash
uv run formsupportagent.py "step2-Eligibility: I am building a transmission line"
```

#### 3. Land Details
```bash
uv run formsupportagent.py "step4-Location-Land-Details-Private-Land: I own this property"
```

---

## Example Results

When the agent runs successfully, it identifies the correct field from the JSON schema and provides a structured JSON response.

### Input: 
`"step3-Add-Well: Status is fully constructed"`

### Output:
```json
{
  "ID": "WorksStatus_100848618_N0",
  "Description": "status of the well construction",
  "SuggestedValue": "Fully Constructed"
}
```

### Input:
`"step3-Add-Well: what is my provincial ID?"`

### Output:
> The provincial ID for a well is known as the **Well Tag Number**. You should enter it in this field:
```json
{
  "ID": "WellTagNumber_100850245_N0",
  "Description": "The provincial identifier for the well record.",
  "SuggestedValue": ""
}
```

---

## A2A Server (FastAPI)

To run the agent as a background service for other agents to call:

1.  **Start the server**:
    ```bash
    uv run formsupport_agent_a2a_server.py
    ```
2.  **Invoke via API**:
    Send a `POST` request to `http://localhost:8001/invoke` with the following body:
    ```json
    {
      "step_number": "step3-Add-Well",
      "query": "Where do I put my well depth?"
    }
    ```

---

## Troubleshooting
- **Warning: Step identifier is required**: You forgot the `step-name:` prefix in your query string.
- **Warning: No prompt template (.md) found**: You have a `.json` schema but forgot to create its corresponding `.md` file in the `prompttemplates/` folder.
