# NR CSS AI Form Support Agent

## Overview

The **NR CSS AI Form Support Agent** is an intelligent form field suggestion assistant that helps users navigate BC Government permit application forms. This agent uses Azure OpenAI to intelligently map user questions to specific form fields and provide contextual suggestions based on form definitions.

## Features

- **Intelligent Field Mapping**: Automatically matches user queries to relevant form fields using semantic understanding
- **Contextual Suggestions**: Provides suggested values based on form field options
- **JSON-based Form Definitions**: Flexible form structure using JSON configuration files
- **Azure OpenAI Powered**: Leverages advanced language models for accurate field matching
- **Async Architecture**: Built with Python's asyncio for efficient request handling
- **Utility Package Integration**: Uses the shared `utils` package for form context processing

## Architecture

The Form Support Agent uses the Microsoft Agent Framework to:
1. Load form field definitions from JSON files
2. Accept user queries about form fields
3. Match queries to form field IDs, titles, and descriptions using semantic analysis
4. Return matching field information with suggested values in JSON format
5. Handle "No Match" scenarios when queries don't align with any form fields

## Prerequisites

- Python 3.13 or higher
- `uv` package manager
- Azure OpenAI account with deployed chat model
- Form definition JSON files in the `formdefinitions` directory

## Installation

1. Navigate to the agent directory:
   ```bash
   cd agentic_ai_backend/agents/formsupportagent
   ```

2. Install dependencies using `uv`:
   ```bash
   uv sync
   ```

## Configuration

Create a `.env` file in the `formsupportagent` directory with the following variables:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=your-deployment-name
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | The endpoint URL for your Azure OpenAI resource |
| `AZURE_OPENAI_API_KEY` | API key for Azure OpenAI authentication |
| `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME` | Name of your deployed chat model |

## Usage

### Running the Agent

Execute the agent with a query:

```bash
uv run formsupportagent.py "your query here"
```

### Examples

**Example 1: Matching a form field**
```bash
uv run formsupportagent.py "Northern Coast Transmission Line"
```

**Output:**
```json
{
  "ID": "isNorthCoastTransmissionLine",
  "Description": "for pilot release, applications related to the north coast transmission line cannot be supported using ai assistant.",
  "SuggestedValue": "Yes"
}
```

**Example 2: No match scenario**
```bash
uv run formsupportagent.py "test query"
```

**Output:**
```
No Match
```



## Project Structure

```
formsupportagent/
├── formsupportagent.py     # Main agent implementation
├── pyproject.toml          # Project dependencies and metadata
├── .env                    # Environment variables (not in version control)
├── README.md               # This file
├── uv.lock                 # Locked dependency versions
└── formdefinitions/        # Form definition JSON files
    └── step2.json          # TODO: THIS will come from blob storage or database
```

## Dependencies

- **agent-framework-core** (>=1.0.0b251211): Microsoft Agent Framework
- **azure-storage-blob** (>=12.27.1): Azure Blob Storage SDK
- **python-dotenv** (>=1.2.1): Environment variable management
- **utils** (0.1.0): Local utility package for form context processing

## Form Definition Structure

Form definitions are stored as JSON files in the `formdefinitions` directory. Ideally this will be stored in a blob storage or a database. This is work-in-progress.

## How It Works

1. **Form Loading**: The agent loads form definitions from JSON files using `get_form_context()`
2. **Context Building**: Form fields are converted into a structured string format for the LLM
3. **Query Processing**: User queries are passed to the agent's `run()` method
4. **Semantic Matching**: The Azure OpenAI model compares the query against field titles and descriptions
5. **Response Generation**: The agent returns:
   - **Match**: JSON with `ID`, `Description`, and `SuggestedValue`
   - **No Match**: Plain text "No Match"

## Agent Instructions

The agent is configured with the following behavior:
- Act as a form field suggestion assistant
- Map user questions to form field IDs
- Match queries using semantic understanding (including synonyms)
- Return only the first matching field if multiple matches exist
- Select an appropriate suggested value from the options list
- Output results in JSON format
- Return "No Match" when no fields align with the query

## Troubleshooting

### Import Error: No module named 'utils'

The `utils` package must be installed as a dependency. Ensure you've run:
```bash
uv sync
```

If the issue persists, verify that `utils` is listed in `pyproject.toml` dependencies and reinstall:
```bash
uv add ../../utils
```

### File Not Found: formdefinitions/step2.json

Ensure you're running the agent from the `formsupportagent` directory:
```bash
cd agentic_ai_backend/agents/formsupportagent
uv run formsupportagent.py "your query"
```

### Missing Environment Variables

If you get `KeyError` for environment variables, verify:
1. The `.env` file exists in the `formsupportagent` directory
2. All required variables are defined
3. The `load_dotenv()` call is executing before variable access

### Agent Returns "No Match" for Valid Queries

Check:
1. The form definition JSON file contains the expected fields
2. The query uses terms similar to field titles or descriptions
3. The Azure OpenAI deployment is functioning correctly

## Development

### Adding New Form Definitions

1. Create a new JSON file in the `formdefinitions` directory
2. Follow the form definition structure outlined above
3. Update the `json_path` in the `dryrun()` function or pass it dynamically

### Testing

Run the agent with various queries to test field matching:

```bash
# Test eligibility matching
uv run formsupportagent.py "Am I eligible for a water licence?"

# Test housing-related matching
uv run formsupportagent.py "Is this for housing units?"

# Test no-match scenario
uv run formsupportagent.py "random unrelated query"
```

### Extending the Agent

To add additional capabilities:

1. **Custom Tools**: Add new tools to the agent initialization
2. **Multi-Step Forms**: Load multiple form definitions and merge contexts
3. **Validation Logic**: Add pre/post-processing for field validation
4. **Blob Storage Integration**: Load form definitions from Azure Blob Storage instead of local files

## Future Enhancements

- [ ] Support for multi-step form navigation
- [ ] Integration with Azure Blob Storage for dynamic form loading
- [ ] Field validation and error handling
- [ ] Support for conditional field logic
- [ ] Calculate costing based on form fields interacting with tools

