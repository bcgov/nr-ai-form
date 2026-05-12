# NR CSS AI Conversation Agent

## Overview

The **NR CSS AI Conversation Agent** is an intelligent assistant designed to support BC Government's Permit Application process. This agent uses Azure AI Search Knowledge Base agentic retrieval to answer user queries about permit applications.

## Features

- **Azure AI Search Agentic Retrieval**: Uses message-based knowledge base retrieval with answer synthesis
- **Async Architecture**: Built with Python's asyncio for efficient request handling
- **Environment-based Configuration**: Secure credential management via environment variables

## Architecture

The Conversation Agent uses the Microsoft Agent Framework to:
1. Accept user queries about permit applications
2. Send chat-style `messages` to the Azure AI Search knowledge base retrieve API
3. Let Azure AI Search perform retrieval planning and answer synthesis
4. Return search results to the user

## Prerequisites

- Python 3.13 or higher
- `uv` package manager
- Azure AI Search service with a configured knowledge base

## Installation

1. Navigate to the agent directory:
   ```bash
   cd agentic_ai_backend/agents/conversationagent
   ```

2. Install dependencies using `uv`:
   ```bash
   uv sync
   ```

## Configuration

Create a `.env` file in the `conversationagent` directory with the following variables:

```env
# Azure AI Search Knowledge Base Configuration
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_SEARCH_API_KEY=your-search-api-key
AZURE_SEARCH_KNOWLEDGE_AGENT_NAME=your-knowledge-base-name
AZURE_SEARCH_KNOWLEDGE_AGENT_API_VERSION=2025-11-01-preview
AZURE_SEARCH_KNOWLEDGE_AGENT_REQUEST_MODE=messages
AZURE_SEARCH_KNOWLEDGE_AGENT_OUTPUT_MODE=answerSynthesis
AZURE_SEARCH_KNOWLEDGE_AGENT_REASONING_EFFORT=low
AZURE_SEARCH_KNOWLEDGE_AGENT_MAX_OUTPUT_SIZE=6000
AZURE_SEARCH_KNOWLEDGE_AGENT_MAX_RUNTIME_SECONDS=30
AZURE_SEARCH_KNOWLEDGE_AGENT_MAX_HISTORY_MESSAGES=10
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `AZURE_SEARCH_ENDPOINT` | The endpoint URL for your Azure AI Search service |
| `AZURE_SEARCH_API_KEY` | API key for Azure AI Search authentication |
| `AZURE_SEARCH_KNOWLEDGE_AGENT_NAME` | Name of the Azure AI Search knowledge base to query |
| `AZURE_SEARCH_KNOWLEDGE_AGENT_API_VERSION` | Knowledge base retrieve API version. Use `2025-11-01-preview` or newer for `messages` |
| `AZURE_SEARCH_KNOWLEDGE_AGENT_REQUEST_MODE` | Retrieval input mode. Use `messages` for agentic retrieval; `intents` is kept only for legacy compatibility |
| `AZURE_SEARCH_KNOWLEDGE_AGENT_OUTPUT_MODE` | Retrieval output mode. Use `answerSynthesis` for synthesized answers or `extractiveData` for raw extracted data |
| `AZURE_SEARCH_KNOWLEDGE_AGENT_REASONING_EFFORT` | Agentic retrieval reasoning effort: `minimal`, `low`, or `medium` |
| `AZURE_SEARCH_KNOWLEDGE_AGENT_MAX_OUTPUT_SIZE` | Maximum KB response size. Must be greater than `5000`; default is `6000` |
| `AZURE_SEARCH_KNOWLEDGE_AGENT_MAX_RUNTIME_SECONDS` | Maximum runtime per retrieve request. Default is `30` |
| `AZURE_SEARCH_KNOWLEDGE_AGENT_MAX_HISTORY_MESSAGES` | Number of prior chat messages to keep in the session. Default is `10` |

## Usage

### Running the Agent

Execute the agent with a query:

```bash
uv run conversationagent.py "your query here"
```

### Example

```bash
uv run conversationagent.py "What are the requirements for a water permit application?"
```


## Project Structure

```
conversationagent/
├── conversationagent.py    # Main agent implementation
├── pyproject.toml          # Project dependencies and metadata
├── .env                    # Environment variables (not in version control)
├── README.md               # This file
└── uv.lock                 # Locked dependency versions
```

## Dependencies

- **agent-framework-core** (1.3.0): Microsoft Agent Framework core
- **agent-framework-openai** (1.3.0): Included for compatibility with adjacent agent components
- **azure-search-documents** (12.0.0): Azure AI Search SDK with knowledge base retrieval support
- **azure-storage-blob** (12.28.0): Azure Blob Storage SDK
- **python-dotenv** (1.2.2): Environment variable management

## How It Works

1. **Initialization**: The agent is initialized with Azure AI Search knowledge base settings
2. **Query Processing**: User queries are passed to the agent's `run()` method
3. **Retrieval**: The agent calls the Azure AI Search knowledge base retrieve API with chat-style `messages`
4. **Session Context**: The agent preserves recent user and assistant turns per session
5. **Response**: Search results are returned to the user

### Agent Framework GA Note

This agent now bypasses direct LLM orchestration in the service and calls Azure AI Search Knowledge Base retrieval directly. The repo currently pins `azure-search-documents==12.0.0`, so the code sends the preview `messages` request using the SDK's raw model mapping even though the installed typed constructor has not caught up to the preview signature yet.

## Agent Instructions

The agent is configured with the following instructions:
- Answer using the configured Azure AI Search knowledge base
- Return only the retrieved response (no additional commentary)

## Troubleshooting

### Import Errors

If you encounter `ModuleNotFoundError` for the `tools` module, ensure you're running the agent from the correct directory or set the `PYTHONPATH`:

```bash
export PYTHONPATH="../../"  # Unix/Mac
$env:PYTHONPATH = "../../"  # Windows PowerShell
```

### Missing Environment Variables

If you get `KeyError` for environment variables, verify:
1. The `.env` file exists in the `conversationagent` directory
2. All required variables are defined
3. The `load_dotenv()` call is executing before variable access

### Azure AI Search Returns No Results

Check:
1. Your knowledge base is configured and contains searchable content
2. The knowledge base name in `.env` matches your Azure resource
3. The search API key has read permissions
4. The query matches indexed content

### Invalid `max output size`

If Azure returns `Configuration max output size must be greater than 5000`, set `AZURE_SEARCH_KNOWLEDGE_AGENT_MAX_OUTPUT_SIZE` to a value above `5000`. The sample configuration uses `6000`.

### `messages` Is Not A Valid Parameter

If Azure returns `The parameter 'messages' in the request payload is not a valid parameter`, verify that:
1. `AZURE_SEARCH_KNOWLEDGE_AGENT_API_VERSION` is `2025-11-01-preview` or newer
2. Your endpoint supports the preview knowledge base retrieve contract
3. `AZURE_SEARCH_KNOWLEDGE_AGENT_REQUEST_MODE=messages`

If you are temporarily stuck on a legacy endpoint, set `AZURE_SEARCH_KNOWLEDGE_AGENT_REQUEST_MODE=intents` as a compatibility fallback.

## Development

### Running Tests

```bash
uv run conversationagent.py "test query"
```

### Adding New Tools

To add additional tools to the agent:

1. Create a new tool in the `tools` directory
2. Import the tool in `conversationagent.py`
3. Add it to the `tools` parameter in the agent initialization


