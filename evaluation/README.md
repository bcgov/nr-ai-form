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

- **AZURE_OPENAI_API_KEY**: Your Azure OpenAI API key
- **AZURE_OPENAI_ENDPOINT**: Your Azure OpenAI endpoint URL
- **AZURE_OPENAI_API_VERSION**: API version
- **AZURE_OPENAI_DEPLOYMENT**: Model deployment name
- **BACKEND_API_URL**: Backend API URL for testing
- **ENABLED_EVALUATORS**: Comma-separated list of evaluators to run
- **LOG_LEVEL**: Logging level (DEBUG, INFO, WARNING, ERROR)

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
