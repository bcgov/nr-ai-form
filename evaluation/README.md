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

- **System under test:** the tenant-aware API gateway WebSocket (`/ws`), forwarding to the GPT-5.1 orchestrator.
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
    backend_client.py     # shared persistent WebSocket / optional HTTP transport
  promptfoo/
    promptfooconfig.js    # SUT=backend, grader=GPT-5.1 (Foundry, az login)
    providers/backend_provider.py
    redteam.js            # safety / jailbreak / prompt-injection suite
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
    custom_backend_target.py  # shared transport, isolated multi-turn conversations
    custom_azure_openai_target.py  # adversarial GPT-5.1 (api-key or az login)
    pyrit_runner.py  orchestrator.py  attack_scenarios.py
    crescendo_step_capture.py  pyrit_security.py  config.py
  pyproject.toml
  .env.example
```

## Setup

```bash
cd evaluation
cp .env.example .env          # configure gateway, tenant ID, allowed Origin and judge
az login                      # judge + promptfoo use your Azure AD session

# Python (DeepEval + dataset builder)
pip install -e ".[dev]"

# Node (Promptfoo)
cd promptfoo && npm install && cd ..
```

Use Node.js 22 or later for Promptfoo. The Python red-team integration supports
PyRIT 1.x (`>=1.0.1,<2`).

### Gateway configuration

Set `BACKEND_API_URL` to the API gateway's `ws://.../ws` or `wss://.../ws`,
`BACKEND_WS_CLIENT_ID` to an **existing configured tenant**, and
`BACKEND_WS_ORIGIN` to an Origin allowed by that tenant. Set
`BACKEND_WS_APPLICATION_ID` to a dedicated test application when needed.
The gateway closes unknown tenants and disallowed Origins; random client IDs
cannot be used as tenant IDs.

The shared transport and PyRIT configuration load `evaluation/.env` regardless
of the working directory. The Promptfoo scripts load the same file explicitly.
Promptfoo's JavaScript configs read the judge host/version directly from the
environment: the pinned version does not interpolate these YAML config fields.
The generated case matrix remains YAML.

```bash
python -m tools.ws_smoke_test
```

The shared client preserves sessions in the connection query as well as the
payload. PyRIT keeps a persistent socket per conversation and closes it after
execution. Crescendo history forks/edits start a fresh session and replay retained
user turns; backend assistant replies are regenerated, not injected from history.
This is a black-box transport limitation to consider when interpreting backtracks.

Current `master` no longer exposes orchestrator `POST /invoke`. HTTP remains
available only when explicitly selecting a compatible legacy service or
`tools/local_backend.py`. The latter is a simple model stand-in, **not** evidence
that the deployed application's tools, retrieval or tenant policies work.

## 1. Build / refresh the golden dataset

```bash
python datasets/build_golden.py \
  --xlsx "<path-to-local-PoC-spreadsheet.xlsx>"
```

Regenerate whenever the spreadsheet changes. Check `summary.json` for the
step/severity distribution and any `low_step_confidence` rows to hand-verify.

## 2. Promptfoo (matrix + gating)

```bash
cd promptfoo
npm run eval          # run against the live backend, grade with GPT-5.1
npm run view          # open the web report
npm run eval:ci       # fail if pass rate < 69% (human PoC baseline)
npm run redteam       # adversarial suite
npm run redteam:report
```

## 3. DeepEval (deep metrics)

Two modes, selected by `EVAL_LIVE`:

```bash
# Offline calibration — grade the historical PoC answers (no backend needed)
EVAL_LIVE=0 pytest deepeval

# Live — re-run the configured gateway per case
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

Real multi-turn adversarial attacks against the live backend. All attack types
use an explicit policy-violation scorer. CLI commands exit nonzero for detected
policy violations, transport/harness failures, missing results, or unscored
(`UNDETERMINED`) outcomes; an attack `FAILURE` means the model resisted.
Reports are still saved for failed scan/seed runs. The adversarial
(attack-generating) model defaults to the GPT-5.1 Foundry judge via Azure AD.
PoC-seeded attack cases live in the gitignored `datasets/redteam/`. Full details
in `redteam/README.md`.

## 5. Offline regression checks

```bash
pytest tests
cd promptfoo && npm test
```

The `Evaluation regression` GitHub Actions workflow runs these checks on relevant
pull requests and pushes without model credentials or PoC data. Python tests exercise a local
fake tenant gateway, session continuity/reconnection/history forks, error frames,
scorer configuration, case-step forwarding and CLI failure gates. Node tests run
the actual Promptfoo CLI and verify that 68% fails, 69% passes, and a provider
error fails even at a 99% pass rate. The pinned CLI uses
`PROMPTFOO_PASS_RATE_THRESHOLD`, not a `--fail-on-threshold` option.
This is harness validation, not a live model-quality or safety certification.
Run the live suites separately against a configured test tenant before merging.

## Canonical steps

`step0-Bot, step1-Introduction, step2-Eligibility, step3-Technical-Information
(+subtypes), step4-Location, step5-File-Upload, step6-Privacy-Confirmation,
step7-Applicant, step9-Declarations, step10-Complete, all-steps`

## Roadmap
- Surface retrieved chunks from `/invoke` → add DeepEval `FaithfulnessMetric`.
- Emit tool-call traces from the orchestrator → enable `ToolCorrectnessMetric`.
- Expand the golden set as more human-labelled batches arrive.
