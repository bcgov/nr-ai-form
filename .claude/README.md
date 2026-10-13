# `.claude/` — Claude Code project configuration

This directory holds **project-level** Claude Code configuration that is shared across the team. User-level config lives in `~/.claude/` and is not part of this repo.

## Layout

```
.claude/
├── README.md                       # this file
├── settings.json                   # shared settings (committed)
├── settings.local.json             # personal overrides (gitignored — see .example)
├── settings.local.json.example     # template to copy when you want personal overrides
└── commands/                       # custom /slash-commands
    ├── sync-all.md
    ├── test-agents.md
    ├── run-stack.md
    ├── orchestrate.md
    └── new-step.md
```

You can also add an `agents/` directory here with `*.md` files to define project-specific subagents — there are none yet.

## `settings.json`

Project-wide permissions, env vars, and hooks. The committed `settings.json` is intentionally conservative:

- **`allow`** — read-only / dev-loop commands run without prompting (`uv sync`, `uv run pytest`, `uv run python`, `docker ps`, `docker logs`, `curl http://localhost:*`, etc.).
- **`ask`** — actions that mutate shared or local state and should be confirmed each time (`docker-compose up/down/build`, starting agent servers, `terraform`/`terragrunt`, `gh pr create/merge`, `git push`).
- **`deny`** — hard-blocked: reading any `.env` / `dev.env` / `test.env` (these contain real credentials in this repo), force pushes, `terraform destroy`, `rm -rf`.

If a permission rule is too tight or too loose for the way you work, **don't change `settings.json`** — copy `settings.local.json.example` to `settings.local.json` and override there.

## Slash commands

Each `.md` file under `commands/` becomes a `/<filename>` command. They are project-scoped, so they only show up when Claude Code is launched from this repo.

| Command | What it does |
|---|---|
| `/sync-all` | `uv sync` across `utils/` + the three agent services. `--include-backend` to also sync the legacy `backend/`. |
| `/test-agents [pytest-args]` | Run pytest in `orchestrators/` and `formsupportagent/` in parallel and summarise results. |
| `/run-stack` | Start `agentic_ai_backend/docker-compose.yaml` (orchestrator + 2 agents + Redis + Cosmos emulator). Verifies `.env` files first. |
| `/orchestrate <query>` | POST a query to `http://localhost:8002/invoke` and print the curated response. |
| `/new-step <stepN-Slug>` | Scaffold a new FormSupportAgent step: JSON definition, prompt template, `stepmappers.js` entry, intent-mapper entry. |

To add a new command, drop a new `.md` file in `commands/`. The frontmatter `description:` is what shows up in autocomplete; the body is the prompt Claude will follow when the command is invoked.

## What `settings.local.json` is for

Personal overrides that should **not** be committed. Common uses:

- Allowing tools that the rest of the team doesn't use (e.g. your preferred `gh` subcommands).
- Setting per-developer env vars for hooks.
- Tightening permissions further than the team default if you want extra confirmation.

Copy from the example:

```powershell
Copy-Item .claude/settings.local.json.example .claude/settings.local.json
```

## Why `.env` files are denied at the read level

`agentic_ai_backend/agents/*/dev.env` and `test.env` are committed to this repo and **contain real-looking Azure OpenAI / Redis credentials**. The `Read(.env)` deny rule prevents Claude from accidentally surfacing these in summaries or PR descriptions. If you genuinely need to inspect one, do it yourself in your terminal.
