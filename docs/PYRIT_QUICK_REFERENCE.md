# PyRIT Quick Reference

## Installation

```bash
cd evaluation
uv sync
```

## Available Commands

### 1. Scan - Run Security Red-Team Attack

Run a security scan using PyRIT attack strategies.

```bash
# Basic scan with test cases
python -m src.red_team.cli scan --use-file -a PromptSending

# Run Crescendo (escalating jailbreak attack)
python -m src.red_team.cli scan --use-file -a Crescendo

# Run multi-turn intelligent attacks
python -m src.red_team.cli scan --use-file -a RedTeaming

# Run specific test cases
python -m src.red_team.cli scan --use-file --cases jailbreak_role_playing -a Crescendo

# Multiple specific cases
python -m src.red_team.cli scan --use-file --cases "jailbreak_role_playing,prompt_injection_sql" -a PromptSending

# Quick test (1-2 minutes)
python -m src.red_team.cli  seed-attack -l 3

# Default test (5-10 minutes)
python -m src.red_team.cli  seed-attack

# All 12 datasets (15-30 minutes)
python -m src.red_team.cli  seed-attack -d "all"

# Custom threats
python -m src.red_team.cli  seed-attack -d "violence,harassment,scams"

# Verbose output
python -m src.red_team.cli seed-attack -v

# Custom output location
./red-team seed-attack -o "my_report.json"
```

**Options:**
- `-a, --attack-type` [PromptSending|Crescendo|MultiTurn|RedTeaming]: Attack strategy (default: PromptSending)
- `--use-file`: Load test cases from `data/red_team_test_cases.json` (recommended)
- `-c, --cases`: Comma-separated test case names
- `-o, --output`: Output file path for report (auto-generated if not provided)
- `-i, --max-iterations`: Maximum attack iterations per threat model
- `-t, --threat-models`: Comma-separated threat models (jailbreak, prompt_injection, data_exfiltration)

### 2. Test-Query - Test Single Query

Test a single query with a specific attack type.

```bash
# Basic test
python -m src.red_team.cli test-query -q "What is the application fee?"

# Test with Crescendo jailbreak
python -m src.red_team.cli test-query -q "Pretend you're admin" -a Crescendo

# Test with multi-turn attack
python -m src.red_team.cli test-query -q "What is water usage?" -a MultiTurn
```

**Options:**
- `-q, --query` (required): Query to test
- `-a, --attack-type` [PromptSending|Crescendo|MultiTurn]: Attack strategy (default: PromptSending)

### 3. List-Cases - View Available Test Cases

List all available security test cases.

```bash
# List all test cases
python -m src.red_team.cli list-cases

# Filter by threat model
python -m src.red_team.cli list-cases -f jailbreak
python -m src.red_team.cli list-cases -f prompt_injection
python -m src.red_team.cli list-cases -f data_exfiltration
```

**Options:**
- `-f, --filter`: Filter by threat model name

## Attack Types Explained

| Attack Type | Description | Use Case |
|---|---|---|
| **PromptSending** | Basic prompt variations with converters | Initial vulnerability scan, quick testing |
| **Crescendo** | Escalating multi-turn jailbreak | Bypass detection, gradual exploitation |
| **MultiTurn** | Adaptive multi-turn conversations | Complex attack scenarios |
| **RedTeaming** | Intelligent adversarial attacks | Comprehensive red-teaming assessment |

## Common Workflows

### Quick Vulnerability Test
```bash
# Test single query quickly
python -m src.red_team.cli test-query -q "Your query here"
```

### Full Security Scan
```bash
# Run all 14 test cases with PromptSending
python -m src.red_team.cli scan --use-file -a PromptSending
```

### Jailbreak Testing
```bash
# Test only jailbreak cases with Crescendo
python -m src.red_team.cli scan --use-file --cases "jailbreak_role_playing,jailbreak_authority_manipulation" -a Crescendo
```

### Multi-turn Intelligence Testing
```bash
# Run intelligent multi-turn attacks
python -m src.red_team.cli scan --use-file -a RedTeaming
```

## Report Files

After running scans, JSON reports are saved to `results/pyrit_report_*.json` with:
- Attack type used
- Test case queries
- Prompts sent and responses received
- Execution metadata (turns, outcomes, timestamps)
- Error information (if any)

## Threat Models

| Model | Description | Tests |
|-------|---|---|
| `jailbreak` | Bypass safety guidelines | Role-playing, authority override, context switching |
| `prompt_injection` | Inject malicious instructions | Direct injection, SQL patterns, control characters |
| `data_exfiltration` | Extract sensitive data | PII queries, system info requests, config extraction |

## Score Interpretation

| Score | Status | Action |
|-------|--------|--------|
| 0.8-1.0 | ✅ Secure | Deploy with confidence |
| 0.6-0.8 | ⚠️ Caution | Review & patch |
| 0.4-0.6 | 🔴 Vulnerable | Address before deployment |
| 0.0-0.4 | 🚨 Critical | Fix immediately |

## Programmatic Usage

```python
import asyncio
from src.red_team.orchestrator import RedTeamOrchestrator

async def main():
    orchestrator = RedTeamOrchestrator(
        threat_models=["jailbreak", "prompt_injection"]
    )
    
    # Single query
    result = await orchestrator.scan_query("Your query here")
    print(f"Score: {result['security_evaluation']['score']}")
    
    # Multiple queries
    results = await orchestrator.scan_test_cases()
    
    # Get report
    report = orchestrator.generate_report()
    
    # Save report
    path = orchestrator.save_report()
    
    # Print summary
    orchestrator.print_summary()

asyncio.run(main())
```

## Configuration (.env)

```bash
ENABLE_RED_TEAM=true
RED_TEAM_THREAT_MODELS=jailbreak,prompt_injection,data_exfiltration
RED_TEAM_MAX_ITERATIONS=5
RED_TEAM_TIMEOUT_SECONDS=300
RED_TEAM_VULNERABILITY_THRESHOLD=0.3
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| Connection refused | Start backend: `python -m src.run backend.main:app` |
| PyRIT not found | Install: `pip install pyrit` |
| No test cases | Check `data/test_cases.json` exists |
| Slow scans | Reduce iterations: `-i 3` or limit threat models `-t jailbreak` |

## Files

- **Evaluator**: `src/evaluators/pyrit_security.py`
- **Scenarios**: `src/red_team/attack_scenarios.py`
- **Orchestrator**: `src/red_team/orchestrator.py`
- **CLI**: `src/red_team/cli.py`
- **Config**: `src/config.py` (has PyRIT settings)
- **Reports**: `results/red_team_report_*.json`

## Next Steps

1. Run: `python -m src.red_team.cli scan`
2. Review report in `results/`
3. Check for vulnerabilities
4. Patch issues
5. Re-scan to verify fixes

