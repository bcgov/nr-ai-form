# AI Evaluation Suite

Comprehensive evaluation framework for NR AI Agentic Backend using Azure AI Evaluation SDK and PyRIT security red-teaming.

## Quick Start

### Security Red-Teaming (Recommended)
```bash
cd evaluation
uv sync
python -m src.red_team.cli scan --use-file -a PromptSending
```

### Quality Evaluation
```bash
cd evaluation
uv sync
cp .env.example .env
python -m src
```

## What Can You Do?

### Security Red-Teaming

Test your application against adversarial attacks using PyRIT:

```bash
# Quick vulnerability scan (PromptSending)
python -m src.red_team.cli scan --use-file -a PromptSending

# Jailbreak-specific testing (Crescendo)
python -m src.red_team.cli scan --use-file -a Crescendo --cases jailbreak_role_playing

# Intelligent red-teaming (RedTeaming)
python -m src.red_team.cli scan --use-file -a RedTeaming

# Test single query
python -m src.red_team.cli test-query -q "What is the application fee?"

# View available test cases
python -m src.red_team.cli list-cases
```

**Threats Tested:**
- Jailbreak attacks (role-playing, authority manipulation, hypothetical scenarios)
- Prompt injection (SQL, JSON, system override, subprompt)
- Data exfiltration (PII extraction, tech stack discovery)
- Validation bypass

### Quality Evaluation

Measure AI output quality:
- **Groundedness**: Verify facts are grounded in context
- **Code Vulnerability**: Detect code security issues
- **Safety**: Check for harmful content

## Documentation

### Security Red-Teaming Guides

| Guide | Purpose |
|-------|---------|
| [Quick Reference](../docs/PYRIT_QUICK_REFERENCE.md) | Command reference and common workflows |
| [Setup Guide](../docs/PYRIT_SETUP_GUIDE.md) | Complete setup and configuration |
| [Test Cases Guide](../docs/PYRIT_TEST_CASES_GUIDE.md) | 14 security test cases explained |
| [Attack Strategies](../docs/PYRIT_ATTACK_STRATEGIES.md) | Attack types: PromptSending, Crescendo, MultiTurn, RedTeaming |
| [Custom Backend Guide](../docs/PYRIT_CUSTOM_BACKEND_GUIDE.md) | CustomBackendTarget implementation details |

## Evaluation Modes

### 1. Security Red-Teaming
Automated adversarial testing using PyRIT framework:
- **PromptSending**: Quick baseline with text converters (1-5 min)
- **Crescendo**: Escalating jailbreak attacks (5-10 min)
- **MultiTurn**: Adaptive multi-turn attacks (10-20 min)
- **RedTeaming**: Intelligent LLM-guided attacks (20-60 min)

Run with:
```bash
python -m src.red_team.cli scan --use-file -a <AttackType>
```

### 2. Quality Evaluation
Measure AI output quality using Azure Evaluation SDK.

Run with:
```bash
python -m src
```

## Project Structure

```
evaluation/
├── README.md                      # This file
├── data/
│   └── red_team_test_cases.json  # 14 security test cases
├── results/
│   └── pyrit_report_*.json       # Generated security reports
├── src/
│   ├── red_team/
│   │   ├── cli.py                # CLI interface
│   │   ├── custom_backend_target.py  # Custom PyRIT target
│   │   ├── pyrit_runner.py       # Attack orchestration
│   │   └── orchestrator.py       # Test case management
│   └── config.py                 # Configuration
└── .env.example                  # Environment template
```

## Setup

### 1. Install Dependencies

```bash
cd evaluation
uv sync
```

### 2. Configure Environment

```bash
cp ../.env.example ../.env
# Add BACKEND_API_URL for custom backend attacks
```

### 3. Run Your First Scan

```bash
# Basic scan
python -m src.red_team.cli scan --use-file -a PromptSending

# View detailed output
python -m src.red_team.cli scan --use-file -a PromptSending
```

### 4. Check Reports

Reports are saved to `results/pyrit_report_YYYYMMDD_HHMMSS.json`:
```bash
# List all reports
ls -la results/

# View latest report
cat results/pyrit_report_*.json | python -m json.tool | head -100
```

## Common Commands

### Test Single Query
```bash
python -m src.red_team.cli test-query -q "Your test query" -a PromptSending
```

### View Test Cases
```bash
python -m src.red_team.cli list-cases
python -m src.red_team.cli list-cases -f jailbreak
```

### Run Specific Cases
```bash
python -m src.red_team.cli scan --use-file \
  --cases "jailbreak_role_playing,prompt_injection_sql" \
  -a Crescendo
```

### Save to Custom Location
```bash
python -m src.red_team.cli scan --use-file \
  -a PromptSending \
  -o /tmp/security_report.json
```

## Attack Types Explained

| Attack | Description | Time | Best For |
|--------|---|---|---|
| **PromptSending** | Text converters on single turn | 1-5 min | Quick scan |
| **Crescendo** | Escalating multi-turn jailbreak | 5-10 min | Jailbreak testing |
| **MultiTurn** | Adaptive multi-turn attacks | 10-20 min | Complex scenarios |
| **RedTeaming** | Intelligent LLM-guided attacks | 20-60 min | Comprehensive audit |

See [Attack Strategies Guide](../docs/PYRIT_ATTACK_STRATEGIES.md) for detailed explanation.

## Test Cases Overview

14 security test cases covering:
- **Jailbreak**: 5 cases (role-playing, authority, hypothetical, etc.)
- **Prompt Injection**: 6 cases (SQL, JSON, system override, etc.)
- **Data Exfiltration**: 2 cases (PII, tech stack discovery)
- **Baseline**: 1 legitimate query for comparison

See [Test Cases Guide](../docs/PYRIT_TEST_CASES_GUIDE.md) for all 14 cases.

## Integration with Backend

### Custom Backend API

The framework automatically detects and attacks your custom backend API:

```bash
# Set in environment
export BACKEND_API_URL=https://your-api.com/invoke

# Attacks are automatically routed to your backend
python -m src.red_team.cli scan --use-file -a PromptSending
```

Your backend receives requests like:
```json
{
  "query": "Attack prompt here",
  "session_id": "uuid",
  "step_number": "2"
}
```

See [Custom Backend Guide](../docs/PYRIT_CUSTOM_BACKEND_GUIDE.md) for implementation details.

## Reports

After running scans, reports are saved as JSON with:
- Attack type and configuration
- Test case queries
- Actual prompts sent to backend
- Responses received from backend
- Execution metadata (turns, outcomes, timestamps)
- Error information (if any)

Example:
```bash
results/pyrit_report_20260710_233315.json
```

Reports contain full turn-by-turn attack transcripts for analysis and remediation.

## Troubleshooting

### Backend Connection Issues
```bash
# Test backend connectivity
curl -X POST https://your-api.com/invoke \
  -H "Content-Type: application/json" \
  -d '{"query":"test","session_id":"test","step_number":"2"}'
```

### Configuration Issues
```bash
# Verify environment
python -c "from src.config import settings; print(settings.backend_api_url)"
```

### Test Single Query First
```bash
# Quick test to diagnose issues
python -m src.red_team.cli test-query -q "What is the application fee?"
```

See [Setup Guide](../docs/PYRIT_SETUP_GUIDE.md) troubleshooting section for more.

## Next Steps

1. 📖 Read [Quick Reference](../docs/PYRIT_QUICK_REFERENCE.md) for command reference
2. 🔍 View test cases: `python -m src.red_team.cli list-cases`
3. ⚡ Run quick scan: `python -m src.red_team.cli scan --use-file -a PromptSending`
4. 📊 Analyze reports in `results/` directory
5. 🔐 Review [Test Cases Guide](../docs/PYRIT_TEST_CASES_GUIDE.md) for vulnerability details
6. 🎯 Choose [Attack Strategy](../docs/PYRIT_ATTACK_STRATEGIES.md) for deeper testing

## References

- **[PyRIT GitHub](https://github.com/Azure/PyRIT)** - Official repository
- **[PyRIT Documentation](https://microsoft.github.io/PyRIT/)** - Complete documentation
- **[OWASP Prompt Injection](https://owasp.org/www-community/attacks/Prompt_Injection)** - Security background

## Documentation Index

All PyRIT documentation in `docs/`:
- `PYRIT_QUICK_REFERENCE.md` - Commands and examples
- `PYRIT_SETUP_GUIDE.md` - Complete setup guide
- `PYRIT_TEST_CASES_GUIDE.md` - 14 test cases explained
- `PYRIT_ATTACK_STRATEGIES.md` - Attack type comparison and usage
- `PYRIT_CUSTOM_BACKEND_GUIDE.md` - Custom target implementation
- `PYRIT_MIGRATION_GUIDE.md` - Migration from other frameworks
- `PYRIT_SECURITY_GUIDE.md` - Security best practices
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
