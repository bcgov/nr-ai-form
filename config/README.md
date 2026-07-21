# Configuration Management System

This directory contains the centralized environment variable configuration system for the NR AI Form project.

## 📂 Structure

```
config/
├── variables.yaml              # Single source of truth for all variables
├── README.md                   # This file
└── schema.json                 # (future) JSON Schema for validation
```

## 🎯 Purpose

**Before:** Environment variables were scattered across multiple files
- `.github/workflows/.deployer_aca.yml` (3 env blocks)
- `terragrunt/terragrunt.hcl`
- `infra/variables.tf`
- `infra/modules/container-apps/variables.tf`
- 6 agent `.env` files

**Now:** Single YAML file with automatic generation to all downstream configs

## 📖 Files

### `variables.yaml`

The authoritative source for all 32 environment variables used in the project.

**Structure:**
```yaml
variables:
  - name: VARIABLE_NAME
    category: "Category"
    type: "variable" | "secret"
    description: "What this does"
    source: "GitHub vars" | "GitHub secrets"
    targets: [list of files this affects]
    terraform_type: "string" | "number" | "bool"
    terraform_sensitive: true | false
    terraform_default: '""'
    agent_default: "value"
    agent_targets: ["agent-name"]  # optional
```

**To edit:**
```bash
# 1. Open config/variables.yaml
# 2. Make changes
# 3. Validate
python scripts/generate-configs.py --validate
# 4. Regenerate affected files
python scripts/generate-configs.py --target <name>
```

## 🤖 Auto-Generation: `scripts/generate-configs.py`

Python script that reads `variables.yaml` and generates all downstream files.

**Install dependencies:**
```bash
pip install pyyaml
```

**Usage:**
```bash
# Validate configuration
python scripts/generate-configs.py --validate

# Generate specific target
python scripts/generate-configs.py --target github-actions
python scripts/generate-configs.py --target terragrunt
python scripts/generate-configs.py --target terraform
python scripts/generate-configs.py --target agent-env
python scripts/generate-configs.py --target agent-env --agent orchestrator

# Generate all targets
python scripts/generate-configs.py --target all

# Save output to file
python scripts/generate-configs.py --target terraform > /tmp/tf_vars.txt
```

## 📋 Workflow: Add/Update/Remove Variables

### Adding a New Variable

1. **Edit** `config/variables.yaml`:
```yaml
  - name: NEW_VARIABLE
    category: "My Category"
    type: "variable"
    description: "Description of what this does"
    source: "GitHub vars"
    targets: ["github-actions", "terraform-root"]
    terraform_type: "string"
    terraform_default: '""'
```

2. **Validate**:
```bash
python scripts/generate-configs.py --validate
```

3. **Generate** output for affected files:
```bash
python scripts/generate-configs.py --target github-actions
python scripts/generate-configs.py --target terraform
```

4. **Manually paste** generated content into appropriate files

5. **Commit** both `config/variables.yaml` and updated files

### Changing an Existing Variable

1. **Edit** `config/variables.yaml` (e.g., change default value)
2. **Validate**: `python scripts/generate-configs.py --validate`
3. **Generate** and paste to affected files
4. **Commit** changes

### Removing a Variable

1. **Delete** from `config/variables.yaml`
2. **Validate**: `python scripts/generate-configs.py --validate`
3. **Manually remove** from all affected files (check `targets` field)
4. **Commit** changes

## 🔄 Affected Files by Target

### `github-actions`
Updates: `.github/workflows/.deployer_aca.yml`
- Pre-Migration State Cleanup job env block
- Safety Plan Check job env block
- Terragrunt job env block

### `terragrunt`
Updates: `terragrunt/terragrunt.hcl`
- Local variables (line ~20)
- tfvars generation block (line ~120)

### `terraform`
Updates:
- `infra/variables.tf` (root variables)
- `infra/variables.tf` (module variables) — Actually `infra/modules/container-apps/variables.tf`
- `infra/main.tf` (variable passthrough to module)

### `agent-env`
Updates:
- `agentic_ai_backend/agents/orchestrators/.env`
- `agentic_ai_backend/agents/conversationagent/.env`
- `agentic_ai_backend/agents/formsupportagent/.env`
- `agentic_ai_backend/api_backend/.env`

## ✅ Validation

Always validate before committing:

```bash
# 1. Validate YAML syntax
python scripts/generate-configs.py --validate

# 2. Validate Terraform syntax
cd infra && terraform validate && cd ..

# 3. Validate Terragrunt syntax
cd terragrunt/dev && terragrunt validate && cd ../..

# 4. Review git diff
git diff config/variables.yaml
git diff .github/workflows/.deployer_aca.yml
```

## 📊 Current Variables

**32 total variables across 11 categories:**

| Category | Count |
|----------|-------|
| Azure OpenAI | 4 |
| Azure Search | 3 |
| Azure Document Intelligence | 2 |
| Azure Storage | 3 |
| Azure Blob Storage | 2 |
| Azure Cosmos DB | 3 |
| Tenant Profile | 3 |
| Cache | 5 |
| Redis | 5 |
| CORS | 1 |
| Application Insights | 1 |

## 🎯 Key Fields Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✓ | Variable name (e.g., `AZURE_OPENAI_API_KEY`) |
| `category` | string | ✓ | Logical grouping (for readability) |
| `type` | enum | ✓ | `variable` or `secret` |
| `description` | string | ✓ | What this variable does |
| `source` | string | ✓ | Where value comes from (`GitHub vars` or `GitHub secrets`) |
| `targets` | array | ✓ | Which downstream files need this variable |
| `terraform_type` | string | ✓ | Terraform type (`string`, `number`, `bool`) |
| `terraform_sensitive` | bool | ✗ | Mark as sensitive in Terraform (default: false) |
| `terraform_default` | string | ✗ | Default value in Terraform (default: `""`) |
| `agent_default` | string | ✗ | Default value for .env files |
| `agent_targets` | array | ✗ | Which agents need this (if omitted, all agents) |

## 🚀 Future Enhancements

Potential improvements:

1. **Auto-apply mode** — Directly update files instead of printing
2. **Validation schema** — JSON Schema for stricter validation
3. **Diff tool** — Show changes before applying
4. **Pre-commit hook** — Validate before commit
5. **Environment-specific values** — Different defaults per env (dev/test)
6. **GitHub Actions integration** — Auto-generate on PR

## 📚 Documentation

- **Quick Reference**: See `docs/ENV_VARIABLES_QUICK_REF.md`
- **Full Guide**: See `docs/ENVIRONMENT_VARIABLES_MANAGEMENT.md`

## 🐛 Troubleshooting

### Script not found
```bash
# Ensure you're in repo root
cd /path/to/nr-ai-form
python scripts/generate-configs.py --validate
```

### YAML validation error
Check that each variable has: `name`, `category`, `type`, `description`, `targets`, `terraform_type`

### Module not found
```bash
pip install pyyaml
```

## 📞 Questions?

Refer to:
1. `config/variables.yaml` — Source of truth
2. `docs/ENV_VARIABLES_QUICK_REF.md` — Quick answers
3. `docs/ENVIRONMENT_VARIABLES_MANAGEMENT.md` — Detailed guide
