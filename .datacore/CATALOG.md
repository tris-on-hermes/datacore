# Module Catalog

| Module | Description | Status |
|--------|-------------|--------|
| gtd | Getting Things Done — task capture, inbox processing, org-mode management | built-in |

## Built-in Modules

These ship with datacore and are always available.

### gtd
- **Agents**: inbox-processor, daily-briefing-generator
- **Commands**: /today, /wrap-up, /continue, /tomorrow
- **Tools**: org_parser.py, date_utils.py, context_merge.py

## Installing Modules

Modules are installed by cloning into `.datacore/modules/[name]/` and registering in `install.yaml`:

```yaml
modules:
  - repo: datacore-one/datacore-research
    path: .datacore/modules/research
```

Then run:
```bash
python3 ~/Data/.datacore/lib/context_merge.py rebuild --path ~/Data
```
