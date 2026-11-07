# PyRIT Red-Team Engine

Ported from Jatinder Singh's `origin/evaluation` branch and rewired to this
suite's conventions (shared gateway WebSocket client, GPT-5.1 Azure AI Foundry model,
Azure AD / `az login` auth). This is the deep **security** layer that
complements the DeepEval/Promptfoo **quality** layer.

## Two model roles
- **Objective target** — the water-permit API gateway (`/ws`), the system under attack (`CustomBackendTarget`, multi-turn capable).
- **Adversarial model** — generates the attacks. Defaults to the same GPT-5.1 Foundry deployment used as our eval judge; authenticated with Azure AD when `ADVERSARIAL_API_KEY` is unset (`CustomAzureOpenAITarget`).

## Attack types (PyRIT framework)
`PromptSending` · `Crescendo` (escalating multi-turn jailbreak) · `MultiTurn` ·
`RedTeaming` (intelligent adaptive) · `PromptSeed` (AIRT seed datasets:
illegal/violence/malware/leakage/misinformation/…).

`crescendo_step_capture.py` records the **intermediate escalation steps** of a
Crescendo run — aligning with this project's per-step evaluation theme.

## Install
```bash
cd evaluation
pip install -e ".[redteam]"     # PyRIT 1.x, structlog, aiohttp, click
az login                        # adversarial model auth (no API key needed)
cp .env.example .env            # gateway, configured tenant, allowed Origin, judge
```

## Run
```bash
# From evaluation/, run as a module so package imports resolve:
python -m redteam.cli list-cases
python -m redteam.cli scan --use-file -a PromptSending
python -m redteam.cli scan --use-file -a Crescendo -i 10
python -m redteam.cli scan -a RedTeaming -t jailbreak,data_exfiltration
```
Reports are written to `results/pyrit_report_*.json` relative to the working directory
(`evaluation/` for the commands above).

Use `BACKEND_API_URL=ws(s)://<gateway>/ws`, a configured
`BACKEND_WS_CLIENT_ID`, and an allowed `BACKEND_WS_ORIGIN`. Do not use random
tenant IDs. HTTP `/invoke` is supported only for an explicitly selected compatible
service or the local stand-in, not the current deployed orchestrator.

Each PyRIT conversation has a separate persistent connection and backend session.
Connections are closed after attack execution, including failures. Edited/forked
Crescendo histories are replayed into a fresh session using retained user turns;
the backend regenerates the assistant replies.

All attack types have an explicit policy-violation scorer using the configured
adversarial model. A normal in-role answer is not a violation. `scan`, `test-query`
and `seed-attack` exit nonzero if an attack succeeds (policy violation), a
transport/harness error occurs, responses are missing, or outcomes are unscored.
Objective-side backend messages, not adversarial-model messages, determine
transport validity. Calibrate the judge and rerun live before relying on its
policy classifications.

## Test cases
PoC-seeded attack data lives in `../datasets/redteam/` (crescendo cases derived
from the 35-row PoC xlsx, incl. real PIDs) and is **gitignored** — it must never
be committed to this public repo. Regenerate or supply your own; point the CLI
at it with `--use-file`.

## Files
| File | Role |
|------|------|
| `custom_backend_target.py` | PyRIT target → shared backend transport (multi-turn) |
| `custom_azure_openai_target.py` | Adversarial target (GPT-5.1, api-key **or** AAD) |
| `pyrit_runner.py` | Framework runner: attacks, AIRT seed datasets, memory |
| `orchestrator.py` | Loads cases, runs scans, aggregates results |
| `attack_scenarios.py` | Jailbreak / prompt-injection / data-exfiltration |
| `crescendo_step_capture.py` | Per-step escalation capture |
| `pyrit_security.py` | Security evaluator (0–1 score) |
| `cli.py` | `python -m redteam.cli …` |
| `config.py` | Settings (objective + adversarial models, run limits) |
| `backend_client.py` | Async shim over `shared.backend_client` |

## Provenance
Original implementation by **JatinderSingh** (`origin/evaluation`). Ported here
with: `src.*` imports → package-relative, API-key-only adversarial auth →
optional Azure AD, PromptTarget constructors made keyword-only for PyRIT ≥0.15,
and PoC attack data moved out of version control. The persistent-connection
pattern from Jatinder's WebSocket implementation is consolidated in
`shared/backend_client.py` for Promptfoo, DeepEval, the smoke probe and PyRIT.
