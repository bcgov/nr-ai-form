# AI Evaluation Suite

Comprehensive evaluation framework for NR AI Agentic Backend using Azure AI Evaluation SDK and PyRIT security red-teaming.

## Quick Start

### Quality Evaluation
```bash
cd evaluation
uv sync
cp .env.example .env
python -m src  # Run quality evaluators
```

### Security Red-Teaming
```bash
python -m src.red_team.cli scan  # Run security scan
```

## Evaluation Modes

### 1. Quality Evaluation
Measure AI output quality using Azure Evaluation SDK:
- **Groundedness**: Verify facts are grounded in context
- **Code Vulnerability**: Detect code security issues
- **Safety**: Check for harmful content

Run with:
```bash
python -m src
```

### 2. Security Red-Teaming (NEW!)
Test your application against adversarial attacks using PyRIT:
- **Jailbreak**: Attempts to bypass safety guidelines
- **Prompt Injection**: Tests for injection vulnerabilities
- **Data Exfiltration**: Attempts to extract sensitive data

Run with:
```bash
python -m src.red_team.cli scan
```

See [PyRIT Quick Reference](.personal_docs/PYRIT_QUICK_REFERENCE.md) for commands.

## Setup

1. **Install dependencies:**
   ```bash
   cd evaluation
   uv sync
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Run evaluation:**
   ```bash
   # Quality evaluation
   python -m src
   
   # Security red-teaming
   python -m src.red_team.cli scan
   ```

## Configuration

### Core Settings
- **AZURE_OPENAI_API_KEY**: Azure OpenAI API key
- **AZURE_OPENAI_ENDPOINT**: Azure OpenAI endpoint URL
- **BACKEND_API_URL**: Backend API URL (default: http://localhost:8000)

### Quality Evaluation
- **ENABLED_EVALUATORS**: Comma-separated evaluators (default: groundedness)
- **GROUNDEDNESS_THRESHOLD**: Min score for pass (default: 0.5)
- **CODE_VULNERABILITY_THRESHOLD**: Min score for pass (default: 0.8)

### Security Red-Teaming (PyRIT)
- **ENABLE_RED_TEAM**: Enable red-team tests (default: false)
- **RED_TEAM_THREAT_MODELS**: Models to test (default: jailbreak,prompt_injection,data_exfiltration)
- **RED_TEAM_MAX_ITERATIONS**: Attacks per model (default: 5)
- **RED_TEAM_TIMEOUT_SECONDS**: Test timeout (default: 300)
- **RED_TEAM_VULNERABILITY_THRESHOLD**: Vulnerability threshold (default: 0.3)

### Azure AI Search (Optional)
For dynamic context retrieval:
- **AZURE_SEARCH_ENDPOINT**: Search endpoint
- **AZURE_SEARCH_API_KEY**: Search API key
- **AZURE_SEARCH_INDEX_NAME**: Index name

See [Full Configuration](#configuration-reference) below for all options.

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

## Security Red-Teaming Guide

For comprehensive PyRIT security testing documentation, see:
- [PyRIT Setup Guide](.personal_docs/PYRIT_SETUP_GUIDE.md) - Step-by-step installation
- [PyRIT Security Guide](.personal_docs/PYRIT_SECURITY_GUIDE.md) - Detailed threat models
- [PyRIT Quick Reference](.personal_docs/PYRIT_QUICK_REFERENCE.md) - Command reference

### Quick Commands

```bash
# Run security scan
python -m src.red_team.cli scan

# Test specific threat model
python -m src.red_team.cli scan -t jailbreak

# Test single query
python -m src.red_team.cli test-query -q "Your query here"

# View saved report
python -m src.red_team.cli report -o results/red_team_report_*.json
```

### Score Interpretation

| Score | Status | Action |
|-------|--------|--------|
| 0.8-1.0 | ✅ Secure | Deploy with confidence |
| 0.6-0.8 | ⚠️ Caution | Review & patch |
| 0.4-0.6 | 🔴 Vulnerable | Address before deployment |
| 0.0-0.4 | 🚨 Critical | Fix immediately |

## Evaluators

### Quality Evaluators

#### Groundedness Evaluator
Validates that response facts are grounded in provided context.
- Detects hallucinations
- Score: 0.0-1.0 (1.0 = fully grounded)

#### Code Vulnerability Evaluator
Detects security issues in AI-generated code.
- Identifies SQL injection, code injection, XSS, etc.
- Score: 1.0 = safe, 0.0 = vulnerable

### Security Evaluators (PyRIT)

#### Jailbreak Scenario
Tests ability to bypass safety guidelines through role-playing and instruction override.

#### Prompt Injection Scenario
Tests resistance to malicious instruction injection.

#### Data Exfiltration Scenario
Tests protection against sensitive data extraction attempts.

## Adding New Evaluators

1. Create evaluator file in `src/evaluators/`
2. Inherit from `BaseEvaluator`
3. Implement `__call__` method
4. Export in `src/evaluators/__init__.py`
5. Add to runner in `src/main.py`
6. Enable in `.env`: `ENABLED_EVALUATORS=existing,new_evaluator`

## Output Format

### Quality Evaluation Results
```json
{
  "score": 0.85,
  "reason": "Groundedness score: 0.85 - good (Pass)",
  "metadata": {
    "threshold": 0.5,
    "passed": true,
    "raw_result": {...}
  }
}
```

### Security Evaluation Results
```json
{
  "score": 0.8,
  "reason": "Security score: 0.8 - secure (Secure)",
  "metadata": {
    "threat_models": ["jailbreak", "prompt_injection"],
    "total_attacks": 10,
    "successful_attacks": 2,
    "category": "secure",
    "attacks": [...]
  }
}
```

## Configuration Reference

### All Environment Variables

```bash
# Azure OpenAI
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4

# Backend API
BACKEND_API_URL=http://localhost:8000
BACKEND_API_TIMEOUT=30

# Quality Evaluation
ENABLED_EVALUATORS=groundedness,code_vulnerability
GROUNDEDNESS_THRESHOLD=0.5
CODE_VULNERABILITY_THRESHOLD=0.8

# Security Red-Teaming (PyRIT)
ENABLE_RED_TEAM=true
RED_TEAM_THREAT_MODELS=jailbreak,prompt_injection,data_exfiltration
RED_TEAM_MAX_ITERATIONS=5
RED_TEAM_TIMEOUT_SECONDS=300
RED_TEAM_VULNERABILITY_THRESHOLD=0.3

# Azure AI Search (Optional)
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net/
AZURE_SEARCH_API_KEY=your-key
AZURE_SEARCH_INDEX_NAME=your-index
AZURE_SEARCH_TOP=3
AZURE_SEARCH_QUERY_TYPE=simple

# Logging
LOG_LEVEL=INFO
EVALUATION_RUN_NAME=evaluation_run
EVALUATION_SCENARIO=basic_evaluation
```

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
