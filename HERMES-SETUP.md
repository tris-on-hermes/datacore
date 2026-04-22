# Hermes Datacore Setup

Hermes-native datacore installation for Tris.

## Installation Manifest

See `install.yaml` for the canonical list of spaces and modules.

### Spaces

| # | Name | Repo | Type |
|---|------|------|------|
| 0 | personal | local | personal |
| 2 | datacore | datacore-one/datacore-space | team (upstream-only) |
| 3 | plur | plur-ai/plur-space | team |

### Modules

| Module | Repo | Status |
|--------|------|--------|
| gtd | datacore-one/datacore-gtd | active |
| outbox | datacore-one/datacore-outbox | active |
| research | datacore-one/datacore-research | active |
| ventures | datacore-one/datacore-ventures | active |
| voice-terminal | datacore-one/datacore-voice-terminal | active |
| whatsapp | datacore-one/datacore-whatsapp | active |
| crm | datacore-one/datacore-crm | active (external) |
| comms | datacore-one/datacore-comms | active (external, v2.0.0) |

## Setup History

1. **Phase 1** — Cloned `datacore-one/datacore` template into `~/Data`
2. **Phase 2** — Reconciled fork history with upstream (revert+merge strategy)
3. **Phase 3** — Integrated spaces and modules, configured gateway

### Gateway

- Hermes gateway installed as systemd user service
- `hermes-gateway.service` enabled with linger (survives reboots)
- Telegram bot @TrisHermes_bot connected

### Git Authentication

- PAT with `repo` + `workflow` scope stored in `~/.git-credentials`
- Git identity: Tris <tris@datacore.one>
- Fork: `tris-on-hermes/datacore` (origin = fork, upstream = datacore-one/datacore)

## Feature Branches on Fork

| Branch | Purpose | Status |
|--------|---------|--------|
| `feature/space-manager` | `.datacore/lib/space_manager.py` — add/list/remove/init team spaces | Ready to PR upstream |
| `feature/hermes-setup` | This setup manifest and installation config | Hermes-specific |

## Upstream Contributions

- `datacore-one/datacore-space`: `.gitignore` — ignore auto-generated `CLAUDE.md` and `SCAFFOLDING.md`

## What's Relevant for PLUR-Hermes

The following patterns and tools from this setup are directly transferable to a `plur-hermes` installation:

1. **`context_merge.py rebuild`** — Rebuilds composed CLAUDE.md files across root, spaces, and modules. PLUR spaces use the same layered context pattern.
2. **`.gitignore` patterns for spaces and modules** — Team spaces (`/[0-9]-*/`) and module repos should never be tracked by the root template.
3. **`install.yaml` manifest** — Records which spaces and modules are active. PLUR's `venture.yaml` could reference a similar manifest.
4. **Gateway + Telegram setup** — The systemd user service pattern (`hermes gateway install`, linger enabled) works for any Hermes installation.
5. **Fork workflow** — `main` tracks `upstream/main` exactly; all custom code lives on feature branches.
6. **Module cloning pattern** — External modules (crm, comms) cloned into `.datacore/modules/<name>/` and gitignored.
7. **`space_manager.py`** — Generic Python tool for managing team spaces. Useful for any multi-space datacore installation.
