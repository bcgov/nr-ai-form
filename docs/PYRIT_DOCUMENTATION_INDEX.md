# PyRIT Documentation Index

Complete documentation for the PyRIT security red-teaming framework integration.

## 📚 Documentation Structure

### Getting Started
Start here if you're new to PyRIT:
1. **[Quick Reference](./PYRIT_QUICK_REFERENCE.md)** - Command cheat sheet and common workflows
2. **[Setup Guide](./PYRIT_SETUP_GUIDE.md)** - Complete installation and configuration

### Understanding the System
Learn how the system works:
1. **[Attack Strategies](./PYRIT_ATTACK_STRATEGIES.md)** - Deep dive into 4 attack types
2. **[Test Cases Guide](./PYRIT_TEST_CASES_GUIDE.md)** - All 14 security test cases explained
3. **[Custom Backend Guide](./PYRIT_CUSTOM_BACKEND_GUIDE.md)** - Backend integration details

### Advanced Topics
- **[Evaluation Workflow Demo](./EVALUATION_WORKFLOW_DEMO.md)** - Step-by-step workflow
- **[Implementation Summary](./IMPLEMENTATION_SUMMARY.md)** - Technical summary
- **[Migration Guide](./PYRIT_MIGRATION_GUIDE.md)** - From other frameworks
- **[Security Guide](./PYRIT_SECURITY_GUIDE.md)** - Security best practices

## 🚀 Quick Start

### 1. Install
```bash
cd evaluation
uv sync
```

### 2. Run First Scan
```bash
python -m src.red_team.cli scan --use-file -a PromptSending
```

### 3. View Results
```bash
ls results/pyrit_report_*.json
```

## 📖 Documentation by Use Case

### I want to...

**Run a security test**
→ [Quick Reference](./PYRIT_QUICK_REFERENCE.md) - Commands section

**Understand how attacks work**
→ [Attack Strategies](./PYRIT_ATTACK_STRATEGIES.md) - See the 4 types explained

**Learn about test cases**
→ [Test Cases Guide](./PYRIT_TEST_CASES_GUIDE.md) - All 14 cases with details

**Integrate custom backend**
→ [Custom Backend Guide](./PYRIT_CUSTOM_BACKEND_GUIDE.md) - Implementation guide

**Set up the system**
→ [Setup Guide](./PYRIT_SETUP_GUIDE.md) - Complete configuration

**Fix an issue**
→ [Setup Guide - Troubleshooting](./PYRIT_SETUP_GUIDE.md#troubleshooting) section

**Compare attack types**
→ [Attack Strategies](./PYRIT_ATTACK_STRATEGIES.md#attack-strategies-comparison) - Comparison table

**See a demo workflow**
→ [Evaluation Workflow Demo](./EVALUATION_WORKFLOW_DEMO.md) - Step-by-step example

## 🎯 Attack Strategies at a Glance

| Strategy | Speed | Complexity | Time | Use Case |
|----------|-------|-----------|------|----------|
| PromptSending | ⚡⚡⚡ Fast | Simple | 1-5 min | Quick scan |
| Crescendo | ⚡⚡ Medium | Medium | 5-10 min | Jailbreak testing |
| MultiTurn | ⚡ Slow | High | 10-20 min | Complex attacks |
| RedTeaming | 🐌 Very Slow | Very High | 20-60 min | Full assessment |

**More:** [Attack Strategies Guide](./PYRIT_ATTACK_STRATEGIES.md)

## 🔒 Test Case Categories

- **Jailbreak Attacks** (5): Role-playing, authority manipulation, hypothetical scenarios
- **Prompt Injection** (6): SQL, JSON, system override, subprompt injection
- **Data Exfiltration** (2): PII extraction, tech stack discovery
- **Baseline** (1): Legitimate query for comparison

**More:** [Test Cases Guide](./PYRIT_TEST_CASES_GUIDE.md)

## 💻 Common Commands

### Full Security Scan
```bash
python -m src.red_team.cli scan --use-file -a PromptSending
```

### Jailbreak Testing
```bash
python -m src.red_team.cli scan --use-file -a Crescendo --cases jailbreak_role_playing
```

### Test Single Query
```bash
python -m src.red_team.cli test-query -q "Your query" -a Crescendo
```

### List Test Cases
```bash
python -m src.red_team.cli list-cases -f jailbreak
```

**More:** [Quick Reference - Commands](./PYRIT_QUICK_REFERENCE.md#available-commands)

## 🔧 Configuration

### Environment Variables
```bash
# Backend API for custom attacks
export BACKEND_API_URL=https://your-api.com/invoke

# Threat models to test (optional)
export RED_TEAM_THREAT_MODELS=jailbreak,prompt_injection

# Max iterations (optional)
export RED_TEAM_MAX_ITERATIONS=5
```

**More:** [Setup Guide - Configuration](./PYRIT_SETUP_GUIDE.md#step-3-configure-environment)

## 📊 Understanding Reports

Reports are saved to `results/pyrit_report_YYYYMMDD_HHMMSS.json` with:
- Attack type and strategy used
- Original test case query
- Actual prompts sent to backend
- Backend responses received
- Execution metadata (turns, outcomes)
- Errors (if any)

**Example:** [Setup Guide - Report Generation](./PYRIT_SETUP_GUIDE.md#report-generation)

## 🚨 Troubleshooting

### Issue: Backend connection errors
**Solution:** [Setup Guide - Troubleshooting](./PYRIT_SETUP_GUIDE.md#troubleshooting)

### Issue: Empty prompts/responses in reports
**Solution:** Reports now properly capture all data - update if seeing issues

### Issue: Choosing right attack type
**Solution:** [Attack Strategies - Decision Tree](./PYRIT_ATTACK_STRATEGIES.md#choosing-the-right-attack-strategy)

## 📁 Document Overview

| Document | Focus | Read Time |
|----------|-------|-----------|
| [Quick Reference](./PYRIT_QUICK_REFERENCE.md) | Commands and examples | 5 min |
| [Setup Guide](./PYRIT_SETUP_GUIDE.md) | Installation and config | 15 min |
| [Attack Strategies](./PYRIT_ATTACK_STRATEGIES.md) | Attack type deep dive | 20 min |
| [Test Cases Guide](./PYRIT_TEST_CASES_GUIDE.md) | 14 test cases detailed | 15 min |
| [Custom Backend Guide](./PYRIT_CUSTOM_BACKEND_GUIDE.md) | Backend implementation | 20 min |
| [Evaluation Workflow Demo](./EVALUATION_WORKFLOW_DEMO.md) | Step-by-step example | 10 min |
| [Implementation Summary](./IMPLEMENTATION_SUMMARY.md) | Technical summary | 10 min |
| [Migration Guide](./PYRIT_MIGRATION_GUIDE.md) | From other frameworks | 15 min |
| [Security Guide](./PYRIT_SECURITY_GUIDE.md) | Best practices | 10 min |

## 🎓 Learning Path

**Beginner:** Read in this order
1. [Quick Reference](./PYRIT_QUICK_REFERENCE.md) - Get familiar with commands
2. [Setup Guide](./PYRIT_SETUP_GUIDE.md) - Set up your system
3. Run: `python -m src.red_team.cli list-cases`
4. Run: `python -m src.red_team.cli test-query -q "test"`

**Intermediate:** Understand the attacks
1. [Attack Strategies](./PYRIT_ATTACK_STRATEGIES.md) - Learn 4 attack types
2. [Test Cases Guide](./PYRIT_TEST_CASES_GUIDE.md) - Understand what's being tested
3. Run different attack types and compare results

**Advanced:** Deep understanding
1. [Custom Backend Guide](./PYRIT_CUSTOM_BACKEND_GUIDE.md) - How custom target works
2. [Implementation Summary](./IMPLEMENTATION_SUMMARY.md) - Technical details
3. Review source code in `evaluation/src/red_team/`

## 🔗 External Resources

- **[PyRIT GitHub](https://github.com/Azure/PyRIT)** - Official repository
- **[PyRIT Docs](https://microsoft.github.io/PyRIT/)** - Official documentation
- **[OWASP Prompt Injection](https://owasp.org/www-community/attacks/Prompt_Injection)** - Security background
- **[Azure OpenAI](https://learn.microsoft.com/azure/ai-services/openai/)** - Azure AI services

## 📌 Key Concepts

### Attack
A single attempt to exploit a vulnerability using PyRIT.

### Turn
One exchange in a multi-turn attack (prompt sent, response received).

### Test Case
A pre-defined security scenario (jailbreak, injection, exfiltration).

### Threat Model
Category of attacks (jailbreak, prompt_injection, data_exfiltration).

### PromptTarget
Abstraction for the backend being attacked (CustomBackendTarget targets custom API).

### Converter
Text transformation applied to prompts (e.g., past tense, future tense).

## ✅ Verification Checklist

- [ ] Read [Quick Reference](./PYRIT_QUICK_REFERENCE.md)
- [ ] Completed [Setup Guide](./PYRIT_SETUP_GUIDE.md) steps
- [ ] Ran first test: `python -m src.red_team.cli test-query -q "test"`
- [ ] Viewed test cases: `python -m src.red_team.cli list-cases`
- [ ] Ran full scan: `python -m src.red_team.cli scan --use-file -a PromptSending`
- [ ] Reviewed report in `results/` directory
- [ ] Understood [Attack Strategies](./PYRIT_ATTACK_STRATEGIES.md)
- [ ] Reviewed [Test Cases Guide](./PYRIT_TEST_CASES_GUIDE.md)

## 📞 Support

For issues or questions:
1. Check the [Troubleshooting](./PYRIT_SETUP_GUIDE.md#troubleshooting) section
2. Review relevant guide based on your issue
3. Check PyRIT official docs: https://microsoft.github.io/PyRIT/

## 📝 Quick Command Reference

```bash
# Full scan - all 14 cases with PromptSending
python -m src.red_team.cli scan --use-file -a PromptSending

# Jailbreak testing - Crescendo attack
python -m src.red_team.cli scan --use-file -a Crescendo \
  --cases "jailbreak_role_playing,jailbreak_authority_manipulation"

# Intelligent red-team - all cases
python -m src.red_team.cli scan --use-file -a RedTeaming

# Quick test - single query
python -m src.red_team.cli test-query -q "What is the fee?" -a PromptSending

# List cases - all or filtered
python -m src.red_team.cli list-cases
python -m src.red_team.cli list-cases -f jailbreak

# View reports
ls -la results/pyrit_report_*.json
```

---

**Last Updated:** 2026-07-11  
**Framework:** PyRIT 0.14.0+  
**Python:** 3.11+
