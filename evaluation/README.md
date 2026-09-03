# NR AI Form — Evaluation Suite

Per-step evaluation for the water-permit assistant (`agentic_ai_backend`).
Two complementary frameworks plus a golden dataset built from the human PoC
testing spreadsheet.

| Layer | Tool | Purpose |
|-------|------|---------|
| Harness + CI gating | **Promptfoo** | Declarative test matrix across form steps, pass/fail thresholds |
| Deep metrics | **DeepEval** | Groundedness/hallucination (RAG), calculation & tool correctness (livestock MCP calculator), task-completion & clarity per step |
| Security red-team | **PyRIT** (`redteam/`) | Real multi-turn Crescendo / RedTeaming / seed-dataset attacks against the live backend — see `redteam/README.md` |
| Ground truth | **Golden dataset** | 35 human-labelled PoC cases → step-keyed JSONL + promptfoo tests |

- **System under test:** the orchestrator backend (`POST /invoke`), GPT-5.1 powered.
- **Judge / grader:** **GPT-5.1** via Azure AI Foundry, authenticated with **Azure AD (`az login`)** — no API key.

> Note: judge and SUT are the same model family, so *live* grading is partly
> self-evaluating. Offline calibration against the historical PoC answers is not.

## Layout

```
evaluation/
  datasets/
    build_golden.py       # xlsx -> golden.jsonl + golden_tests.yaml + summary.json
    golden.jsonl          # canonical dataset (generated)
    golden_tests.yaml     # promptfoo tests (generated)
  shared/
    backend_client.py     # POST /invoke client + response-text extraction
  promptfoo/
    promptfooconfig.yaml  # SUT=backend, grader=GPT-5.1 (Foundry, az login)
    providers/backend_provider.py
    redteam.yaml          # safety / jailbreak / prompt-injection suite
    package.json
  deepeval/
    azure_judge.py        # GPT-5.1 judge (Azure AD)
    dataset_loader.py     # offline (xlsx) vs live (/invoke) modes
    conftest.py
    test_task_completion.py   # accuracy + clarity, every step
    test_groundedness.py      # hallucination + relevancy, RAG cases
    test_tool_correctness.py  # calculator / tool-call correctness
  redteam/                    # PyRIT security engine (ported) — see redteam/README.md
    cli.py                    # python -m redteam.cli scan -a Crescendo
    custom_backend_target.py  # attacks /invoke (multi-turn)
    custom_azure_openai_target.py  # adversarial GPT-5.1 (api-key or az login)
    pyrit_runner.py  orchestrator.py  attack_scenarios.py
    crescendo_step_capture.py  pyrit_security.py  config.py
  pyproject.toml
  .env.example
```

## Setup

```bash
cd evaluation
cp .env.example .env          # edit if your endpoint/model differ
az login                      # judge + promptfoo use your Azure AD session

# Python (DeepEval + dataset builder)
pip install -e ".[dev]"

# Node (Promptfoo)
cd promptfoo && npm install && cd ..
```

## 1. Build / refresh the golden dataset

```bash
python datasets/build_golden.py \
  --xlsx "C:/Users/prdevar/Documents/workspace/internal/BCGov/water-permit/AI PoC Testing Result & Feedback(1-35).xlsx"
```

Regenerate whenever the spreadsheet changes. Check `summary.json` for the
step/severity distribution and any `low_step_confidence` rows to hand-verify.

## 2. Promptfoo (matrix + gating)

```bash
cd promptfoo
npm run eval          # run against the live backend, grade with GPT-5.1
npm run view          # open the web report
npm run eval:ci       # CI: fail if pass rate < 0.69 (human PoC baseline)
npm run redteam       # adversarial suite
npm run redteam:report
```

## 3. DeepEval (deep metrics)

Two modes, selected by `EVAL_LIVE`:

```bash
# Offline calibration — grade the historical PoC answers (no backend needed)
EVAL_LIVE=0 pytest deepeval

# Live — re-run the backend /invoke per case
EVAL_LIVE=1 pytest deepeval

# Scope to one step
EVAL_LIVE=1 EVAL_STEPS=step3-Technical-Information pytest deepeval/test_task_completion.py
```

Metrics:
- `test_task_completion.py` — **accuracy** (threshold 0.6 ≈ human 3.46/5) and **clarity** (≈ 3.57/5) for every case.
- `test_groundedness.py` — **no-hallucination** + **answer-relevancy** for fee/eligibility/BCeID RAG cases.
- `test_tool_correctness.py` — **calculation guidance** (BC Ag Calculator vs provincial); `ToolCorrectnessMetric` activates once `/invoke` returns tool traces (`EVAL_TOOL_TRACES=1`).

## 4. PyRIT red-team (security)

```bash
pip install -e ".[redteam]"     # heavier deps (pyrit, aiohttp, structlog)
az login                        # adversarial model auth (no key)
python -m redteam.cli scan --use-file -a Crescendo -i 10
```

Real multi-turn adversarial attacks against the live backend. The adversarial
(attack-generating) model defaults to the GPT-5.1 Foundry judge via Azure AD.
PoC-seeded attack cases live in the gitignored `datasets/redteam/`. Full details
in `redteam/README.md`.

## Canonical steps

`step0-Bot, step1-Introduction, step2-Eligibility, step3-Technical-Information
(+subtypes), step4-Location, step5-File-Upload, step6-Privacy-Confirmation,
step7-Applicant, step9-Declarations, step10-Complete, all-steps`

## Roadmap
- Surface retrieved chunks from `/invoke` → add DeepEval `FaithfulnessMetric`.
- Emit tool-call traces from the orchestrator → enable `ToolCorrectnessMetric`.
- Expand the golden set as more human-labelled batches arrive.
