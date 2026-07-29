# CLI Quick Reference - Seed Dataset Attacks

## One-Line Setup & Usage

```bash
# From evaluation directory
cd evaluation
uv sync                    # Install dependencies (or: pip install -e .)
red-team seed-attack       # Run with defaults (20 seeds from 4 datasets)
```

---

## 5 Common Commands

```bash
1️⃣  DEFAULT ATTACK (Quick baseline)
   red-team seed-attack
   → Uses: illegal, violence, hate, sexual (20 seeds)
   → Time: ~5-10 minutes

2️⃣  QUICK TEST (Verify setup)
   red-team seed-attack -l 3
   → Uses: 3 seeds from default datasets
   → Time: ~1-2 minutes

3️⃣  FOCUSED TEST (Specific threats)
   red-team seed-attack -d "violence,harassment,scams"
   → Uses: 3 datasets, ~11 seeds
   → Time: ~3-5 minutes

4️⃣  FULL COVERAGE (Complete assessment)
   red-team seed-attack -d "all"
   → Uses: All 12 datasets, 55 seeds
   → Time: ~15-30 minutes

5️⃣  SAVE REPORT (Custom output)
   red-team seed-attack -o "results/my_report.json"
   → Saves report to specified path
```

---

## All Options

```bash
red-team seed-attack [OPTIONS]

OPTIONS:
  -d, --datasets TEXT        Comma-separated datasets
                             (default: illegal,violence,hate,sexual)
  
  -l, --limit-seeds INTEGER  Max seeds to use (default: all available)
  
  -o, --output PATH          Report output file
                             (default: results/seed_attack_TIMESTAMP.json)
  
  -v, --verbose              Show detailed logging
  
  --help                     Show this help message
```

---

## Dataset Names (12 Total)

```
illegal, violence, hate, sexual, harassment, scams, 
malware, fairness, leakage, misinformation, harms, psychosocial
```

---

## Output Structure

```json
{
  "attack_type": "SeedDataset",
  "seed_datasets": ["illegal", "violence", "hate", "sexual"],
  "total_seeds_used": 20,
  "results": {
    "total_turns": 20,
    "turns": [
      {
        "turn": 1,
        "prompt": "...",
        "response": "..."
      }
    ]
  },
  "timestamp": "2024-01-15T10:30:45Z"
}
```

---

## Real-World Examples

```bash
# 🧪 Lab: Test single threat
red-team seed-attack -d "violence" -v

# 🏗️ Build: Validate all categories
red-team seed-attack -d "all" -o "reports/full_scan.json"

# 🔍 Debug: Quick syntax check
red-team seed-attack -l 1 -v

# 📊 CI/CD: Scheduled daily scan
red-team seed-attack -d "all" \
  -o "reports/daily_$(date +%Y%m%d).json"

# 🎯 Focused: Security audit
red-team seed-attack \
  -d "illegal,violence,hate,malware,scams" \
  -o "reports/security_audit.json"

# ⚡ Production: Quick health check
red-team seed-attack -l 1
```

---

## Help Commands

```bash
red-team --help                    # List all commands
red-team seed-attack --help        # Show seed-attack options
red-team seed-attack -v --help     # Verbose with help
```

---

## Environment Setup (First Time)

```bash
# 1. Navigate to evaluation directory
cd evaluation

# 2. Install Python dependencies
uv sync
# OR
pip install -e .

# 3. Set Azure credentials (if needed)
export AZURE_OPENAI_API_KEY="your-key"
export AZURE_OPENAI_ENDPOINT="https://..."

# 4. Test installation
red-team --help

# 5. Run first attack
red-team seed-attack -l 3 -v
```

---

## Interpreting Results

✅ **Success:**
```
✅ Attack completed successfully!
📋 Attack Summary:
  Total Seeds: 20
  Total Turns: 20
  Timestamp: 2024-01-15T10:30:45Z
💾 Report saved: results/seed_attack_TIMESTAMP.json
```

❌ **Error:**
```
❌ Attack failed: [error message]
```

To debug:
```bash
red-team seed-attack -v                 # Add verbose flag
red-team seed-attack -l 1 -v            # Start with 1 seed
```

---

## Performance Guide

| What | Command | Time |
|------|---------|------|
| Quick test | `red-team seed-attack -l 3` | 1-2 min |
| Default | `red-team seed-attack` | 5-10 min |
| Extended | `red-team seed-attack -d "violence,hate,harassment"` | 8-15 min |
| Full | `red-team seed-attack -d "all"` | 15-30 min |

---

## Scripting Examples

**Bash:**
```bash
#!/bin/bash
cd evaluation
red-team seed-attack -l 5 -v -o "results/test_$(date +%s).json"
```

**Python:**
```python
import subprocess
result = subprocess.run([
    "red-team", "seed-attack", 
    "-d", "illegal,violence",
    "-l", "5",
    "-v"
], capture_output=True, text=True)
print(result.stdout)
```

**Docker:**
```bash
docker run -it --env-file .env \
  nr-ai-form-backend:latest \
  red-team seed-attack -d "all"
```

---

## Documentation

- **Full Guide:** [CLI_USAGE_GUIDE.md](./CLI_USAGE_GUIDE.md)
- **Implementation Details:** [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)
- **Usage Scenarios:** [SEED_DATASET_USAGE.md](./SEED_DATASET_USAGE.md)
- **Quick Reference:** This file

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| `command not found: red-team` | Run `pip install -e .` in evaluation dir |
| `Invalid dataset 'typo'` | Check spelling: `red-team seed-attack --help` |
| `No API key` | Set `AZURE_OPENAI_API_KEY` environment variable |
| `Timeout` | Try: `red-team seed-attack -l 1 -v` |
| `No results` | Check logs: `red-team seed-attack -v 2>&1 \| tee debug.log` |

---

**TL;DR - Just run this:**
```bash
cd evaluation && uv sync && red-team seed-attack
```
