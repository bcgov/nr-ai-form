# NR CSS AI Conversation Agent

## Overview

The **NR CSS AI Conversation Agent** is an intelligent assistant designed to support BC Government's Permit Application process. This agent leverages Azure OpenAI and Azure AI Search to provide accurate, context-aware responses to user queries about permit applications.

## Features

- **Azure AI Search Integration**: Retrieves relevant information from indexed permit documentation
- **Azure OpenAI Powered**: Uses advanced language models for natural conversation
- **Async Architecture**: Built with Python's asyncio for efficient request handling
- **Environment-based Configuration**: Secure credential management via environment variables

## Architecture

The Conversation Agent uses the Microsoft Agent Framework to:
1. Accept user queries about permit applications
2. Use the `azure_ai_search` tool to retrieve relevant context from indexed documents
3. Generate responses based on the retrieved information
4. Return search results to the user

## Prerequisites

- Python 3.13 or higher
- `uv` package manager
- Azure OpenAI account with deployed chat model
- Azure AI Search service with indexed permit related documents

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
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=your-deployment-name

# Azure AI Search Configuration
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_SEARCH_API_KEY=your-search-api-key
AZURE_SEARCH_INDEX_NAME=your-index-name
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | The endpoint URL for your Azure OpenAI resource |
| `AZURE_OPENAI_API_KEY` | API key for Azure OpenAI authentication |
| `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME` | Name of your deployed chat model |
| `AZURE_SEARCH_ENDPOINT` | The endpoint URL for your Azure AI Search service |
| `AZURE_SEARCH_API_KEY` | API key for Azure AI Search authentication |
| `AZURE_SEARCH_INDEX_NAME` | Name of the search index containing water permit documents |

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

- **agent-framework-core** (>=1.0.0b251211): Microsoft Agent Framework
- **azure-search-documents** (>=11.6.0): Azure AI Search SDK
- **azure-storage-blob** (>=12.27.1): Azure Blob Storage SDK
- **python-dotenv** (>=1.2.1): Environment variable management

## How It Works

1. **Initialization**: The agent is initialized with Azure OpenAI credentials
2. **Query Processing**: User queries are passed to the agent's `run()` method
3. **Tool Execution**: The agent automatically invokes the `azure_ai_search` tool
4. **Search**: The tool queries the Azure AI Search index for relevant documents
5. **Response**: Search results are returned to the user

## Agent Instructions

The agent is configured with the following instructions:
- Act as an assistant for BC Government's Water Permit Application
- Use the `azure_ai_search` tool to answer user queries
- Return only search results from the tool (no additional commentary)

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
1. Your search index contains documents
2. The index name in `.env` matches your Azure resource
3. The search API key has read permissions
4. The query matches indexed content

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


