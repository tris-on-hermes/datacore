# CLAUDE.md

This file teaches you how to work effectively in this Datacore installation — Hermes Edition.

## Your Memory

You have persistent memory through two systems — use both in every session.

**PLUR** (`plur_*` tools) — engram memory engine. Corrections, preferences, and patterns persist across sessions.
**Datacore** (this context + org files + knowledge base) — GTD productivity, journal, knowledge files, modules.

### Session Workflow

1. **Start**: Call `plur_inject` with task description — injects relevant engrams
2. **Recall**: Before answering factual questions, call `plur_recall` — the answer is in memory
3. **Learn**: When corrected or discovering something new, call `plur_learn`
4. **Feedback**: Rate injected engrams with `plur_feedback` — trains relevance
5. **End**: Call `plur_capture` for journal entry, then update org files if tasks changed

### Datacore Tools (productivity)

- `datacore.capture` — write journal entries and knowledge notes (via skill)
- `datacore.search` — search journal and knowledge files
- `datacore.ingest` — import content into knowledge base
- `datacore.today` — morning briefing workflow
- `datacore.wrap_up` — session close with learning capture
- `datacore.continue` — resume highest-impact work

### Dates — NEVER type from memory

LLMs hallucinate day-of-week names and anchor to training-era years. Rules:

1. **Today's date**: use the date injected into your system prompt — copy it literally. If unsure, call `python3 ~/Data/.datacore/lib/date_utils.py today`.
2. **Day-of-week for any date**: call `python3 ~/Data/.datacore/lib/date_utils.py dow YYYY-MM-DD`. Never compute it in your head.
3. **Relative dates** ("next Monday", "in 3 days"): call `python3 ~/Data/.datacore/lib/date_utils.py parse "next monday"`.
4. **org-mode timestamps**: call `python3 ~/Data/.datacore/lib/date_utils.py org-stamp YYYY-MM-DD` — returns `<YYYY-MM-DD Day>` correctly.
5. **Before writing** a date+dow into any `.org` or `.md` file, verify with `python3 ~/Data/.datacore/lib/date_utils.py validate YYYY-MM-DD Day`.

> **Recall split**: `plur_recall` searches engram memory. `datacore.search` searches journal/knowledge files. For comprehensive results, call both.

## Methodologies

Datacore combines established methodologies with AI augmentation:

- **GTD (Getting Things Done)** — task management. Single capture point (`inbox.org`), clarify/organize into `next_actions.org`, `:AI:` tags delegate to agents. Weekly reviews maintain the system.
- **Zettelkasten** — knowledge management. Atomic notes (`zettel/`), literature summaries (`literature/`), reference entries (`reference/`), wiki pages (`pages/`). Cross-linked for emergent connections.
- **Engram memory** — AI learning via PLUR. Corrections, preferences, and patterns persist across sessions.
- **Modular architecture** — extensibility. Self-contained modules add domain capabilities. Fork-and-overlay contribution model (DIP-0001).

## Spaces

| Space | Purpose | Key Projects |
|-------|---------|-------------|
| **0-personal** | GTD, PKM, personal projects | Health, learning, side projects |
| **2-datacore** | Datacore system development | DIPs, architecture, CLI, modules |

Each space is a separate git repo with its own CLAUDE.md, org files, knowledge base, and journal. When working in a space, its CLAUDE.md loads automatically with space-specific context.

### Personal (0-personal/)

- `org/inbox.org` — single capture point (sacred — always return to clean)
- `org/next_actions.org` — tasks with `:AI:` tags for delegation
- `notes/` — PKM: journals, zettel, literature, pages, reference

### Datacore Development (2-datacore/)

- `org/inbox.org` / `org/next_actions.org` — system tasks tagged with `:AI:`
- `1-tracks/` — active work: ops, product, dev/architecture, research, comms
- `3-knowledge/` — system knowledge: pages, zettel, literature, reference
- `contacts/` — people, companies, projects, events (CRM data)
- `journal/` — daily entries

This space is a direct clone of `datacore-one/datacore-space` (not a fork) — contributions push upstream.

## Finding Things

### Commands & Agents

Agents and commands are registered in `.datacore/registry/`. Don't memorize — look up:
- `plur_recall` — search by name or purpose
- `.datacore/registry/agents.yaml` / `commands.yaml` — full registries

Slash commands (`/today`, `/continue`, `/wrap-up`) are multi-phase workflows. Conversational commands work naturally — "process inbox", "weekly review", "sync repos".

### Knowledge Base

Before starting work, check for existing knowledge:
- `datacore.search` — semantic search across journal and knowledge files
- `plur_recall` — targeted engram retrieval by domain or keywords
- `[space]/3-knowledge/` — permanent knowledge: `zettel/` (concepts), `literature/` (sources), `reference/` (people, companies), `pages/` (wiki)
- `[space]/notes/journal/` — working notes and daily journals

Don't start from scratch when context might already exist.

## Modules

Datacore is extensible via **modules** — self-contained packages that add agents, commands, tools, and context to specific domains. Each lives in `.datacore/modules/<name>/` with a `module.yaml` manifest.

Modules hook into workflows (e.g., adding sections to `/today`), register their own agents, and provide tools. Their CLAUDE.md loads on-demand when the domain is relevant.

Installed modules:
- **crm** (`.datacore/modules/crm/`) — Network intelligence, contacts, relationships, landscape tracking. Triggers: "CRM dashboard", "look up contact", "who do I know at"
- **telegram** (`.datacore/modules/telegram/`) — Notifications via @TrisHermes_bot
- **org** (`.datacore/modules/org/`) — Organization space template (reference)
- **cli** (`.datacore/modules/cli/`) — CLI tooling reference (source code)

<!-- REGISTRY:modules -->

## Infrastructure

<!-- REGISTRY:infrastructure -->

> Server IPs, SSH configs, deployment procedures are in engram memory. Call `plur_recall` with domain "infrastructure". Do NOT guess IPs — always verify via recall.

## Conventions

### Tasks — use org_parser.py

**NEVER grep raw `.org` files for task queries.** Use the org parser, which treats tasks as structured objects:

```bash
# CLI adapter
python3 ~/Data/.datacore/lib/org_parser.py list --file ~/Data/0-personal/org/inbox.org --states TODO
python3 ~/Data/.datacore/lib/org_parser.py add --file ~/Data/0-personal/org/inbox.org "New task" --tags AI
```

### org-mode format

- Headings: `*` per level. States: TODO, NEXT, WAITING, DONE, CANCELLED
- Properties: `:PROPERTIES:` ... `:END:`. Tags: `:tag1:tag2:`
- Timestamps: **Always verify day-of-week** — LLMs get these wrong
- AI Task Tags: `:AI:` (general), `:AI:research:`, `:AI:content:`, `:AI:data:`, `:AI:pm:`, `:AI:technical:` (human review)

### Notes & Tags

- Wiki-links: `[[Page Name]]`. Journal: `YYYY-MM-DD.md`
- Tags: `#tag` in PKM/CRM, `:tag:` in org-mode. NOT frontmatter arrays.
- Registries: `.datacore/tags.yaml` (system), `[space]/.datacore/tags.yaml` (space)

### Bash

- **Never multi-line Bash.** Chain with `&&`.
- Use dedicated tools: `search_files` not `grep`, `read_file` not `cat`.

## System Patterns (DIPs)

Datacore Improvement Proposals define system patterns. Located in the `datacore-dips` repo.

All DIP content should be ingested into PLUR for quick lookups.

### Layered Context (DIP-0002)

All context files use layered privacy: `.base.md` (public) → `.space.md` → `.local.md` (private). Composed `.md` is gitignored. Rebuild: `python ~/Data/.datacore/lib/context_merge.py rebuild --path ~/Data`

## Verification Protocol

When recalling facts that will drive actions (server IPs, file paths, API endpoints, credential locations):
1. State the recalled fact explicitly before acting on it
2. Include the engram ID or search that produced it
3. If no engram matches, say "No engram found — verifying from filesystem" and check directly
4. Never interpolate between two engrams to produce a "probably correct" composite
