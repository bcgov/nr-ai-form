# NR Agentic AI Backend

An intelligent agentic AI backend built with FastAPI, LangGraph, and Azure OpenAI that provides intelligent form-filling capabilities through natural language conversation. The system features sophisticated agent orchestration, state management, and AI-powered search integration.

## Overview

The NR Agentic AI Backend transforms the traditional form-filling experience by enabling users to complete complex forms through natural language conversation. The system features:

1. **Intelligent Form Analysis**: Automatically extracts relevant information from user messages and maps it to form fields
2. **Dynamic Field Processing**: Processes individual fields with validation, error handling, and contextual questioning
3. **State-Driven Workflow**: Maintains conversation state and form progress using LangGraph's state management
4. **Azure OpenAI Integration**: Leverages Azure OpenAI for natural language understanding and generation
5. **AI Search Integration**: Enhanced information retrieval using Azure AI Search
6. **Extensible Agent Architecture**: Modular design with specialized agents for different tasks

## Architecture

The backend is built using a modern agentic AI architecture with the following components:

### Core Components

- **FastAPI Application**: RESTful API server with async support
- **LangGraph StateGraph**: Orchestrates the conversation flow and maintains state
- **Azure OpenAI Integration**: Powers natural language understanding and generation
- **Azure AI Search**: Provides semantic search capabilities for form context
- **Agent-Based Processing**: Specialized agents handle different aspects of form filling
- **State Management**: Comprehensive state tracking using LangGraph checkpointing
- **Memory Persistence**: In-memory checkpointing for conversation continuity

### Agent Architecture

1. **Analyze Form Agent** (`formfiller/agents/analyze_form_agent.py`):
   - Extracts information from user messages
   - Maps user input to form field schema
   - Identifies filled and missing fields
   - Integrates with AI search for enhanced context
   - Returns structured JSON with field mappings

2. **Process Field Agent** (`formfiller/agents/process_field_agent.py`):
   - Handles targeted field-specific processing
   - Validates field inputs against field types and options
   - Generates contextual follow-up questions
   - Manages field-level error handling
   - Returns success/failure status with validation messages

### Workflow Process

```
User Input → Analyze Form Agent → AI Search (optional)
                ↓
         Field Mapping & Validation
                ↓
         Missing Fields Identified?
                ↓
         Yes → Process Field Agent → Validate Input
                ↓                           ↓
         No → Complete              Success/Retry
                ↓
         Return Response
```

## Project Structure

```text
backend/
├── __init__.py                    # Backend package initialization
├── main.py                        # Main FastAPI application entry point
├── run.py                         # Application runner script
├── pyproject.toml                 # Project dependencies and configuration
├── uv.lock                        # Lock file for uv package manager
├── Dockerfile                     # Container configuration
├── env.example                    # Environment variables template
├── example_request.json           # Example API request payload
├── README.md                      # This documentation file
├── INTEGRATION_GUIDE.md           # Integration documentation
├── ENVIRONMENT_CONFIG.md          # Environment configuration guide
├── LICENSE                        # License information
│
├── core/                          # Core utilities and configuration
│   ├── __init__.py
│   ├── config.py                  # Configuration management
│   └── logging.py                 # Logging setup
│
├── formfiller/                    # Form-filling agent module
│   ├── __init__.py                # Module exports
│   ├── README.md                  # Detailed formfiller documentation
│   ├── CHAT_REQUEST_VARS.md       # State variables reference
│   ├── graph.py                   # LangGraph workflow and state management
│   ├── api.py                     # Form-filling API endpoints
│   ├── llm_client.py              # Azure OpenAI client configuration
│   │
│   ├── agents/                    # Specialized processing agents
│   │   ├── __init__.py
│   │   ├── analyze_form_agent.py  # Form analysis and extraction
│   │   └── process_field_agent.py # Field processing and validation
│   │
│   ├── prompts/                   # LLM prompt templates
│   │   ├── analyze_form_prompt.py     # Main form analysis prompt
│   │   ├── analyze_form_prompt_ReAct.py  # ReAct pattern (future)
│   │   ├── process_field_prompt.py    # Field processing prompt
│   │   └── backup_prompt.py           # Fallback prompts
│   │
│   └── tools/                     # Agent tools and utilities
│       ├── __init__.py
│       └── ai_search_tool.py      # Azure AI Search integration
│
├── search_indexer/                # Web crawling and indexing
│   ├── __init__.py
│   └── web_crawler.py             # Web content crawler
│
├── notebook/                      # Jupyter notebooks for development
│   ├── form_filling_agent.ipynb
│   ├── graph.ipynb
│   ├── search.ipynb
│   └── workflow_human.ipynb
│
└── ipynb/                         # Additional notebooks
    └── search.ipynb
```

## Installation and Setup

### Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) package manager (recommended)
- Azure OpenAI service account with deployment
- Azure AI Search service (optional, for enhanced search)

### Installing uv

If you don't have uv installed:

```bash
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or using pip
pip install uv
```

### Project Setup with uv

1. **Clone the repository and navigate to the backend directory**
   ```bash
   git clone <repository-url>
   cd nr-ai-form/backend
   ```

2. **Create and activate virtual environment**
   ```bash
   uv venv
   
   # On macOS/Linux:
   source .venv/bin/activate
   
   # On Windows:
   .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   uv sync
   ```

### Environment Configuration

Create a `.env` file in the `backend` directory with the following configuration:

```bash
# Azure OpenAI Configuration (Required)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_API_KEY=your-api-key

# Azure AI Search Configuration (Optional)
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_SEARCH_KEY=your-search-api-key
AZURE_SEARCH_INDEX_NAME=your-index-name

# Logging Configuration
LOG_LEVEL=INFO

# Optional: Redis for conversation persistence
# REDIS_URL=redis://localhost:6379
```

See `env.example` for a complete template.

## Running the Application

### Development Mode

From the `backend` directory:

```bash
# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Run with auto-reload
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or using the run script
uv run python run.py

# Or run from project root
cd ..
uv run python -m backend.main
```

### Production Mode

```bash
# Run without auto-reload
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Docker

```bash
# Build the image
docker build -t nr-ai-backend .

# Run the container
docker run -p 8000:8000 --env-file .env nr-ai-backend
```

## API Reference

### Main Endpoints

#### Health Check
```http
GET /health
```

Returns the health status of the API.

**Response:**
```json
{
  "status": "healthy",
  "service": "NR Agentic AI API"
}
```

#### Process Form Request
```http
POST /api/process
```

Main endpoint for form processing with the orchestrator agent.

**Request Body:**
```json
{
  "message": "I want to apply for a water licence. My name is John Smith",
  "formFields": [
    {
      "data_id": "field-1-1",
      "fieldType": "text",
      "is_required": true,
      "fieldValue": "",
      "fieldLabel": "What is your Name?",
      "fieldContext": "Provide your first and last name",
      "required": true
    }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Thanks John! I've captured your name. Could you tell me more about the purpose of your water licence application?",
  "formFields": [
    {
      "data_id": "field-1-1",
      "fieldType": "text",
      "is_required": true,
      "fieldValue": "John Smith",
      "fieldLabel": "What is your Name?",
      "fieldContext": "Provide your first and last name",
      "required": true
    }
  ]
}
```

### Form-Filling Endpoints

The form-filling agent provides additional endpoints under `/api/form/`:

#### Chat with Form Agent
```http
POST /api/form/chat
```

Conversational interface for form completion.

**Request Body:**
```json
{
  "user_message": "My name is John Smith and email is john@example.com",
  "form_fields": [
    {
      "data_id": "name",
      "fieldLabel": "Full Name",
      "fieldType": "text",
      "fieldValue": null,
      "is_required": true,
      "options": null
    }
  ],
  "thread_id": "optional-thread-id"
}
```

**Response:**
```json
{
  "thread_id": "uuid-generated-id",
  "response_message": "Thanks! I've captured your name and email.",
  "status": "awaiting_info",
  "filled_fields": [
    {
      "data_id": "name",
      "fieldValue": "John Smith"
    }
  ],
  "missing_fields": [
    {
      "data_id": "phone",
      "fieldLabel": "Phone Number"
    }
  ]
}
```

For detailed API documentation, visit `http://localhost:8000/docs` when the server is running.

## State Management

The system uses LangGraph's state management to maintain conversation context:

### FormFillerState Structure

```python
{
  "user_message": str,              # Current user input
  "form_fields": list,              # Form field definitions
  "filled_fields": list,            # Successfully filled fields
  "missing_fields": list,           # Fields needing input
  "current_field": Optional[list],  # Field being processed
  "conversation_history": list,     # Chat history
  "status": Literal[...],           # Workflow status
  "response_message": str,          # Agent response
  "thread_id": str                  # Conversation ID
}
```

Status values:
- `in_progress`: Agent is processing
- `awaiting_info`: Waiting for user input
- `completed`: Form is complete

See `formfiller/CHAT_REQUEST_VARS.md` for complete state variable documentation.

## Key Features

### AI-Powered Form Analysis

The system uses sophisticated prompt engineering to:
- Extract information from natural language
- Map user input to structured form fields
- Validate data against field constraints
- Generate contextual follow-up questions

### Azure AI Search Integration

Enhanced information retrieval using:
- Semantic search over indexed documents
- Context-aware field suggestions
- Dynamic form help text generation

### Robust Error Handling

- Field validation with custom rules
- Graceful error recovery
- Detailed error messages for users
- Comprehensive logging for debugging

### Extensible Architecture

- Modular agent design
- Pluggable tools and search providers
- Customizable prompts
- Support for custom field types

## Development

### Adding New Agents

Create a new agent in `formfiller/agents/`:

```python
from langchain.chains import LLMChain
from ..llm_client import llm
from ..prompts.your_prompt import your_prompt

your_agent_executor = LLMChain(
    llm=llm,
    prompt=your_prompt,
    verbose=True
)
```

### Customizing Prompts

Modify prompts in `formfiller/prompts/` to change agent behavior:

```python
from langchain.prompts import PromptTemplate

your_prompt = PromptTemplate(
    template="""Your custom prompt here...""",
    input_variables=["variable1", "variable2"]
)
```

### Adding Tools

Create new tools in `formfiller/tools/`:

```python
from langchain.tools import tool

@tool
def your_custom_tool(query: str) -> str:
    """Tool description"""
    # Implementation
    return result
```

## Testing

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=backend --cov-report=html

# Run specific test file
uv run pytest tests/test_agents.py
```

## Deployment

### Environment Variables

Ensure all required environment variables are set:
- Azure OpenAI credentials
- Azure AI Search credentials (if used)
- Log level configuration

### Docker Deployment

```bash
# Build
docker build -t nr-ai-backend:latest .

# Run
docker run -d -p 8000:8000 --env-file .env nr-ai-backend:latest
```

### Azure Deployment

See `AZURE_DEPLOYMENT.md` for detailed Azure deployment instructions.

## Monitoring and Logging

The application uses Python's logging module with configurable log levels:

```bash
# Set log level via environment variable
export LOG_LEVEL=DEBUG

# Logs include:
# - Request/response information
# - Agent execution details
# - Error traces
# - Performance metrics
```

## Troubleshooting

### Common Issues

1. **Azure OpenAI Connection Issues**
   - Verify endpoint and API key
   - Check network connectivity
   - Ensure deployment name is correct

2. **Search Integration Issues**
   - Verify Azure AI Search credentials
   - Check index exists and is populated
   - Review search query syntax

3. **State Management Issues**
   - Check thread_id is consistent across requests
   - Verify checkpointer configuration
   - Review conversation history structure

## Performance Considerations

- Use async endpoints for better concurrency
- Implement request caching where appropriate
- Monitor Azure OpenAI token usage
- Consider rate limiting for production
- Use Redis for distributed state management

## Contributing

1. Follow existing code structure and patterns
2. Add tests for new features
3. Update documentation for API changes
4. Use type hints throughout
5. Follow PEP 8 style guidelines

## Documentation

- `README.md` (this file): Backend overview and setup
- `formfiller/README.md`: Detailed form-filling agent documentation
- `formfiller/CHAT_REQUEST_VARS.md`: State variable reference
- `INTEGRATION_GUIDE.md`: Integration examples and patterns
- `ENVIRONMENT_CONFIG.md`: Environment configuration details

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## Support

For issues, questions, or contributions, please refer to the project repository.

---

**Version:** 0.1.0  
**Last Updated:** November 2025
