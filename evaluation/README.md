# AI Evaluation Suite

Comprehensive evaluation framework for NR AI Agentic Backend using Azure AI Evaluation SDK.

## Setup

1. **Install dependencies:**
   ```bash
   cd evaluation
   uv sync
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Azure OpenAI credentials
   ```

3. **Run evaluation:**
   ```bash
   # From evaluation directory
   python -m src
   ```

## Configuration

All settings are managed via environment variables (see `.env.example`):

### Required Configuration
- **AZURE_OPENAI_API_KEY**: Your Azure OpenAI API key
- **AZURE_OPENAI_ENDPOINT**: Your Azure OpenAI endpoint URL
- **BACKEND_API_URL**: Backend API URL for testing

### Optional Configuration
- **AZURE_OPENAI_API_VERSION**: API version (default: 2024-02-15-preview)
- **AZURE_OPENAI_DEPLOYMENT**: Model deployment name (default: gpt-4)
- **ENABLED_EVALUATORS**: Comma-separated list of evaluators to run (default: groundedness)
- **LOG_LEVEL**: Logging level (default: INFO)

### Azure AI Search Configuration (Optional)
For context retrieval instead of file-based context:

- **AZURE_SEARCH_ENDPOINT**: Your Azure Search endpoint
- **AZURE_SEARCH_API_KEY**: Your Azure Search API key
- **AZURE_SEARCH_INDEX_NAME**: Index name to search
- **AZURE_SEARCH_TOP**: Number of results to return (default: 3)
- **AZURE_SEARCH_QUERY_TYPE**: Query type - `simple` (default) or `semantic`
  - `simple`: Basic keyword search (always works)
  - `semantic`: Advanced semantic ranking (requires semantic configuration in index)
- **AZURE_SEARCH_SEMANTIC_CONFIGURATION**: Semantic config name (default: default) - only used if semantic search enabled

**Note**: 
- If Azure Search is not configured, the system will automatically fallback to file-based context (`data/context.json`)
- If semantic search is enabled but your index lacks semantic configuration, the system automatically falls back to simple search
- Default is `simple` query type to work with all Azure Search indexes

## Context Retrieval

### Azure AI Search (Recommended)
If Azure Search is configured, context is retrieved dynamically based on each query:
```python
context = load_context(query="What is a permit?")
# Retrieves relevant documents from Azure Search matching the query
# Uses simple or semantic search based on .env configuration
# Automatically falls back to simple if semantic not configured
```

### File-Based Context (Fallback)
If Azure Search is not configured or initialization fails, context is loaded from a static file:
```json
{
  "context": "Your evaluation context here..."
}
```

## Query Types

### Simple Query (Default - Recommended)
- ✅ Works with any Azure Search index
- ✅ Keyword-based search
- ✅ No special configuration needed
- Enabled with: `AZURE_SEARCH_QUERY_TYPE=simple`

### Semantic Query (Advanced)
- 🔍 Semantic ranking for better relevance
- 🔍 Extracts captions and answers
- ⚠️ Requires semantic configuration in index
- Enabled with: `AZURE_SEARCH_QUERY_TYPE=semantic`
- **Automatic Fallback**: If your index doesn't have semantic configuration, the system automatically uses simple search

## Evaluators
### Groundedness Evaluator
Validates that response facts are grounded in provided context.

## Adding New Evaluators

1. Create evaluator file in `src/evaluators/`
2. Inherit from `BaseEvaluator`
3. Implement `__call__` method
4. Export in `src/evaluators/__init__.py`
5. Add to runner in `src/main.py`
6. Enable in `.env`: `ENABLED_EVALUATORS=existing,new_evaluator`

## Output Format

Results include:
- **score**: 0.0-1.0 normalized score
- **reason**: Explanation of the score
- **metadata**: Additional evaluation details

## Development

Run tests:
```bash
pytest
```

Format code:
```bash
black src/
isort src/
```
