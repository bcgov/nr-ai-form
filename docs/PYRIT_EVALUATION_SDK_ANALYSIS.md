# PyRIT vs Azure AI Evaluation SDK: Integration Analysis

## Executive Summary

**TL;DR:** PyRIT and Azure AI Evaluation SDK serve **different purposes** and can be integrated, but they're not directly competitive. Integrating both makes sense **only if your threat model requires red-teaming/adversarial testing** in addition to standard quality metrics.

---

## What Each Tool Does

### Azure AI Evaluation SDK
**Purpose:** Quality & Safety Assessment of AI outputs  
**Scope:** Pre-deployment quality gates  
**Focus:** Measuring performance on expected behavior

**Built-in Evaluators:**
- Groundedness (hallucination detection)
- Coherence (output quality)
- Fluency (natural language quality)
- Relevance (answers match query)
- Code Vulnerability (security scanning)
- Safety (violence, hate, sexual, self-harm)
- Protected Material Detection

**Workflow:**
```
Input Dataset → Azure Evaluators → Pass/Fail Metrics → Report
```

**Your Current Setup:**
- ✅ You're using `GroundednessEvaluator` and `CodeVulnerabilityEvaluator`
- ✅ Custom adapter pattern with consistent `BaseEvaluator` interface
- ✅ Threshold-based pass/fail logic
- ✅ Structured result format (score, reason, metadata)

---

### PyRIT (Python Risk Identification Tool)
**Purpose:** Proactive security testing & red-teaming  
**Scope:** Pre-deployment adversarial attack simulation  
**Focus:** Identifying vulnerabilities before they're exploited

**Core Capabilities:**
- **Red-teaming orchestration:** Automated adversarial attack chains
- **Prompt injection testing:** SQLi, code injection, path traversal
- **Jailbreak attempts:** Test model resistance to harmful requests
- **Scenario-based attacks:** Simulates real-world attack patterns
- **Converter chains:** Compose multiple attack techniques (encryption, obfuscation, encoding)
- **Scoring:** Integrates custom scorers for measuring attack success

**Workflow:**
```
Attack Scenarios → Converter Chains → Model Under Test → Scorers → Attack Success Rate
```

**Comparison:**
| Aspect | Azure Eval SDK | PyRIT |
|--------|---|---|
| **Type** | Metrics Measurement | Attack Simulation |
| **Input** | Normal queries | Adversarial prompts |
| **Goal** | Grade quality | Find vulnerabilities |
| **Automation** | Batch evaluation | Iterative red-team |
| **Time** | Minutes to hours | Hours to days |
| **Output** | Pass/Fail scores | Attack success %, techniques |

---

## Integration Scenarios

### ✅ Makes Sense: Both Tools Together
You should use **both** if:

1. **Your threat model includes adversarial attacks**
   - You're building a public-facing LLM chatbot
   - You're handling sensitive data (PII, medical, financial)
   - You need compliance attestation (SOC 2, ISO 27001)

2. **You want defense-in-depth evaluation**
   ```
   ┌─────────────────────────────────────────┐
   │ Development Pipeline                    │
   ├─────────────────────────────────────────┤
   │ 1. Quality Gate (Azure Eval SDK)        │  ← Is output good quality?
   │    - Groundedness                        │
   │    - Code vulnerability                 │
   │    - Safety metrics                     │
   │                                         │
   │ 2. Security Gate (PyRIT)                │  ← Can it be attacked?
   │    - Jailbreak resistance               │
   │    - Prompt injection prevention        │
   │    - Attack attempt handling            │
   │                                         │
   │ → PASS BOTH → Deploy                   │
   └─────────────────────────────────────────┘
   ```

3. **You need measurable security posture**
   - Track jailbreak attempts over time
   - Measure resilience improvements
   - Report to security/compliance teams

---

### ❌ Doesn't Make Sense: PyRIT Alone for Your Use Case
You **don't need PyRIT** if:

- ✗ You're in a closed/trusted environment (internal only)
- ✗ Your primary concern is output quality (not attacks)
- ✗ You don't have a security/red-team capability
- ✗ Your form-filling agent can't be exploited (simple domain-specific task)

---

## Architecture Options

### Option A: Separate Pipelines (Recommended)

```
Evaluation Framework (Current)
├── Azure AI Evaluation SDK (quality gates)
│   ├── Groundedness
│   ├── Code Vulnerability
│   └── Safety Evaluators
└── PyRIT (security gates) [IF needed]
    ├── Red-team scenarios
    ├── Attack chains
    └── Scorer results
```

**Advantages:**
- ✅ Clear separation of concerns
- ✅ Different cadences (eval runs frequently, red-team runs occasionally)
- ✅ Independent configuration/debugging
- ✅ Easier to disable one without affecting the other

**Implementation:**
```python
# evaluation/src/main.py
from src.evaluators import AzureGroundednessEvaluatorAdapter, ...
from src.red_team import PyRITSecurityEvaluator  # NEW

class EvaluationRunner:
    def __init__(self):
        # Quality metrics
        self.quality_evals = {
            "groundedness": AzureGroundednessEvaluatorAdapter(),
            "code_vulnerability": AzureCodeVulnerabilityEvaluatorAdapter(),
        }
        
        # Security gates (optional, feature-flagged)
        if settings.enable_red_team:
            self.security_evals = {
                "jailbreak_resistance": PyRITSecurityEvaluator(),
            }
```

---

### Option B: Unified Wrapper (Not Recommended)

```python
class UnifiedAIEvaluator(BaseEvaluator):
    """Combine all evaluation types"""
    def __init__(self):
        self.azure_evaluators = [...]
        self.pyrit_evaluator = PyRITSecurityEvaluator()
    
    def __call__(self, response, query, context):
        # Run both in sequence
        azure_result = self.run_azure_evaluators()
        pyrit_result = self.run_pyrit_evaluator()
        
        return {
            "quality": azure_result,
            "security": pyrit_result,
            "overall_pass": azure_result["passed"] and pyrit_result["passed"]
        }
```

**Disadvantages:**
- ✗ Hard to debug individual failures
- ✗ PyRIT is slow (red-teaming takes time) - blocks quality evaluation
- ✗ Overfitting design to your specific use case
- ✗ Mixes different evaluation paradigms

---

## Feasibility Assessment

### Implementation Effort

| Task | Effort | Notes |
|------|--------|-------|
| Add PyRIT to `pyproject.toml` | **5 min** | Single dependency |
| Create `PyRITEvaluatorAdapter` | **2-4 hrs** | Medium complexity |
| Design attack scenarios | **4-8 hrs** | Depends on threat model |
| Integration testing | **4-8 hrs** | PyRIT is orchestrator-heavy |
| CI/CD pipeline changes | **2-4 hrs** | Feature-flag red-team tests |
| **Total** | **18-32 hrs** | 2-4 days of work |

### Dependency Compatibility

**Good News:**
```
✅ PyRIT is MIT licensed (same as your evaluation framework)
✅ PyRIT supports async/batch operations (like Azure SDK)
✅ No conflicts with azure-ai-evaluation dependencies
✅ Both use Python 3.11+ (your env)
✅ PyRIT has adapter pattern for multiple AI backends
```

**Potential Issues:**
```
⚠️  PyRIT adds 50+ transitive dependencies (large footprint)
⚠️  PyRIT uses httpx for async; Azure SDK uses aiohttp (compatible but bloat)
⚠️  PyRIT requires runtime configuration (targets, converters, scorers)
⚠️  Red-team tests are CPU/API-heavy (cost implications)
```

---

## Does It Make Sense for Your Form-Filling Agent?

### Your Current Threat Model
```
Form-Filling Agent
├── Internal use (mostly)
├── Handles form data (structured)
└── Limited NLG (mostly fill/extract)
```

### Risk Assessment

**Low Risk Scenarios (Azure Eval SDK sufficient):**
- ✅ Hallucination in extracted data → `Groundedness`
- ✅ Generated SQL is vulnerable → `CodeVulnerability`
- ✅ Response contains unsafe content → Built-in safety

**High Risk Scenarios (PyRIT would help):**
- ❓ Can attacker inject malicious form data?
- ❓ Can prompt injection bypass form validation?
- ❓ Can jailbreak attempts trick agent into harmful actions?
- ❓ Is there a public API surface?

### Recommendation

**Start with Azure Eval SDK only** ✅

1. **Phase 1:** Establish quality gates (now)
   - Groundedness, code vulnerability, safety
   - Baseline metrics for your agent

2. **Phase 2:** Security assessment (optional)
   - If agent becomes public-facing
   - If handling sensitive/PII data
   - If compliance requires it
   - THEN add PyRIT red-teaming

---

## Implementation Path (If You Decide to Add PyRIT)

### Step 1: Create Adapter Pattern

```python
# evaluation/src/evaluators/pyrit_adapter.py
from pyrit.orchestrator import PromptSendingOrchestrator
from pyrit.models import AttackStrategy
from src.evaluators.base import BaseEvaluator

class PyRITSecurityEvaluator(BaseEvaluator):
    """Adapter for PyRIT red-teaming"""
    
    def __init__(self, threat_model: str = "jailbreak"):
        self.threat_model = threat_model
        self.orchestrator = self._init_orchestrator()
    
    def __call__(self, response: str, query: str = "", **kwargs):
        # Run red-team attack scenarios
        attack_results = self.orchestrator.run_red_team(query)
        
        # Score vulnerability
        vulnerability_score = self._calculate_vulnerability(attack_results)
        
        return self.normalize_result(
            score=vulnerability_score,
            reason=f"Red-team vulnerability score: {vulnerability_score}",
            metadata={"attacks": attack_results}
        )
```

### Step 2: Feature-Flag It

```python
# evaluation/src/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing config ...
    enable_red_team_evaluation: bool = False
    pyrit_threat_model: str = "jailbreak"
    pyrit_max_iterations: int = 10
```

### Step 3: Integrate Into Pipeline

```python
# evaluation/src/main.py
if settings.enable_red_team_evaluation:
    all_evals["security"] = PyRITSecurityEvaluator(
        threat_model=settings.pyrit_threat_model
    )
```

---

## Cost Implications

### Azure Eval SDK (Your Current)
- Groundedness: ~$0.01-0.02 per evaluation
- Code Vulnerability: ~$0.01-0.02 per evaluation
- **For 1,000 evals:** ~$20-40

### PyRIT Red-Teaming (If Added)
- Each attack chain: ~$0.05-0.10 per LLM call
- Typical attack: 5-10 chains per test
- **For 100 red-team tests:** ~$50-100

**Total Stack Cost:** ~$70-140 for comprehensive evaluation

---

## Verdict

| Question | Answer |
|----------|--------|
| **Should you implement PyRIT?** | **Not now** - sufficient with Azure Eval SDK |
| **Does it make technical sense?** | **Yes** - clean separation possible |
| **Are they compatible?** | **Yes** - no conflicts |
| **Can you run both?** | **Yes** - but in separate pipelines |
| **When to add PyRIT?** | If/when your threat model changes (public API, sensitive data, compliance) |

---

## Minimal Viable Implementation (If You Change Your Mind)

If you want to **experiment with PyRIT without full integration:**

```bash
# 1. Install
pip install pyrit

# 2. Quick test
python -m pyrit --list-attack-scenarios

# 3. Run simple red-team
from pyrit.orchestrator import PromptSendingOrchestrator
orchestrator = PromptSendingOrchestrator.from_config()
results = orchestrator.run_red_team_test(
    target="your-form-agent",
    attack_type="jailbreak",
    iterations=5
)
```

**Effort:** 1-2 hours to get initial results

---

## Next Steps

### If You Want to Stay Azure-Only ✅
- Continue with current Azure Eval SDK adapters
- Add more evaluators as needed (fluency, relevance, etc.)
- Keep structure clean for future additions

### If You Want to Experiment with PyRIT
1. Create a branch: `feature/pyrit-red-team`
2. Install PyRIT and run quick tests
3. Assess findings against your threat model
4. Decide if recurring red-team tests are valuable

### If You Need Full Security Pipeline
1. Implement PyRIT adapter (following pattern above)
2. Add to CI/CD on separate schedule
3. Track metrics over time
4. Use for compliance reporting

