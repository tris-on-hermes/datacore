#!/usr/bin/env python3
"""
Layered Context Merge Utility — Hermes Edition

Merges context files across permission levels:
- .base.md   (PUBLIC)  - Generic template, PRable to upstream
- .space.md  (SPACE)   - Space-specific, tracked in space repo
- .local.md  (PRIVATE) - Personal customizations, always gitignored

Output: Composed .md file (gitignored, read at runtime)

Registry injection: <!-- REGISTRY:xxx --> markers in templates are replaced
with auto-generated tables from YAML registries.

See DIP-0002 for full specification.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None

LAYERS = [
    ("base", "PUBLIC"),
    ("space", "SPACE"),
    ("team", "TEAM"),
    ("local", "PRIVATE"),
]

VALIDATED_LAYERS = ("PUBLIC",)

PRIVATE_PATTERNS = [
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'email address'),
    (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', 'phone number'),
    (r'(?i)(api[_-]?key|password|secret|token)\s*[:=]\s*["\']?[A-Za-z0-9]+', 'potential secret'),
    (r'\$[\d,]+\.\d{2}', 'dollar amount'),
]

REGISTRY_MARKER = re.compile(r'<!-- REGISTRY:(\w+) -->')


def _truncate(text: str, max_len: int = 60) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    truncated = text[:max_len].rsplit(" ", 1)[0]
    return truncated + "..."


def _load_yaml(path: Path) -> dict | list | None:
    if yaml is None or not path.exists():
        return None
    with open(path) as f:
        return yaml.safe_load(f)


def _parse_frontmatter(file_path: Path) -> dict:
    if yaml is None or not file_path.exists():
        return {}
    try:
        text = file_path.read_text()
        if not text.startswith("---"):
            return {}
        end = text.index("---", 3)
        fm_block = text[3:end].strip()
        return yaml.safe_load(fm_block) or {}
    except (ValueError, yaml.YAMLError):
        return {}


def _format_triggers(triggers: list, max_shown: int = 3) -> str:
    if not triggers:
        return "-"
    shown = triggers[:max_shown]
    result = ", ".join(shown)
    if len(triggers) > max_shown:
        result += ", ..."
    return result


def _generate_modules_table(modules_dir: Path) -> str:
    if not modules_dir.exists():
        return "_No modules installed._\n"
    rows = []
    for module_yaml in sorted(modules_dir.glob("*/module.yaml")):
        data = _load_yaml(module_yaml)
        if not data:
            continue
        name = data.get("name", module_yaml.parent.name)
        version = data.get("version", "-")
        desc = _truncate(data.get("description", ""), 50)
        provides = data.get("provides", {})
        agents_count = len(provides.get("agents", []))
        commands_count = len(provides.get("commands", []))
        priority = data.get("context", {}).get("priority", "-") if isinstance(data.get("context"), dict) else "-"
        fm = _parse_frontmatter(module_yaml.parent / "CLAUDE.base.md")
        if fm.get("summary"):
            desc = _truncate(fm["summary"], 50)
        if fm.get("context"):
            priority = fm["context"]
        triggers = _format_triggers(fm.get("triggers", []))
        rows.append(f"| {name} | {version} | {desc} | {triggers} | {agents_count} | {commands_count} | {priority} |")
    if not rows:
        return "_No modules installed._\n"
    header = "| Module | Version | Description | Triggers | Agents | Cmds | Context |\n"
    header += "|--------|---------|-------------|----------|--------|------|---------|"
    return header + "\n" + "\n".join(rows) + "\n"


def _generate_agents_table(agents_yaml: Path) -> str:
    data = _load_yaml(agents_yaml)
    if not data:
        return "_No agents registered._\n"
    rows = []
    core_agents = data.get("agents", {})
    if isinstance(core_agents, dict):
        for name, info in core_agents.items():
            if not isinstance(info, dict) or info.get("deprecated"):
                continue
            desc = _truncate(info.get("description", ""))
            rows.append(f"| `{name}` | {desc} | core |")
    module_agents = data.get("module_agents", {})
    if isinstance(module_agents, dict):
        for name, info in module_agents.items():
            if not isinstance(info, dict) or info.get("deprecated"):
                continue
            desc = _truncate(info.get("description", ""))
            module = info.get("module", "-")
            rows.append(f"| `{name}` | {desc} | {module} |")
    if not rows:
        return "_No agents registered._\n"
    header = "| Agent | Description | Module |\n"
    header += "|-------|-------------|--------|"
    return header + "\n" + "\n".join(rows) + "\n"


def _generate_commands_table(commands_yaml: Path) -> str:
    data = _load_yaml(commands_yaml)
    if not data or "commands" not in data:
        return "_No commands registered._\n"
    active_rows = []
    conversational_rows = []
    all_commands = {}
    commands = data.get("commands", {})
    if isinstance(commands, dict):
        all_commands.update(commands)
    module_commands = data.get("module_commands", {})
    if isinstance(module_commands, dict):
        all_commands.update(module_commands)
    for cmd_key, cmd in all_commands.items():
        if not isinstance(cmd, dict):
            continue
        status = cmd.get("status", "active")
        desc = _truncate(cmd.get("description", ""))
        module = cmd.get("module", "core")
        if status == "active":
            active_rows.append(f"| `/{cmd_key}` | {desc} |")
        elif status in ("demoted", "habit"):
            trigger = cmd.get("trigger", "")
            if trigger:
                example = trigger.split("|")[0].strip()
                conversational_rows.append(f"| {desc[:40]} | \"{example}\" | {module} |")
    parts = []
    if active_rows:
        header = "**Slash commands** (multi-phase workflows):\n\n"
        header += "| Command | Description |\n"
        header += "|---------|-------------|"
        parts.append(header + "\n" + "\n".join(active_rows))
    if conversational_rows:
        hint = "\n\n**Conversational** (just say what you need):\n\n"
        hint += "| Action | Example Trigger | Module |\n"
        hint += "|--------|-----------------|--------|"
        parts.append(hint + "\n" + "\n".join(conversational_rows))
    if not parts:
        return "_No commands registered._\n"
    return "\n".join(parts) + "\n"


def _generate_sources_table(sources_yaml: Path) -> str:
    data = _load_yaml(sources_yaml)
    if not data or "sources" not in data:
        return "_No sources configured._\n"
    rows = []
    for source_key, source in data["sources"].items():
        if not isinstance(source, dict):
            continue
        stype = source.get("type", "?")
        desc = _truncate(source.get("description", ""))
        rows.append(f"| `{source_key}` | {stype} | {desc} |")
    if not rows:
        return "_No sources configured._\n"
    header = "| Source | Type | Description |\n"
    header += "|--------|------|-------------|"
    return header + "\n" + "\n".join(rows) + "\n"


def _generate_infrastructure_table(infra_yaml: Path) -> str:
    data = _load_yaml(infra_yaml)
    if not data:
        return "_No infrastructure configured._\n"
    rows = []
    for name, info in data.get("servers", {}).items():
        if not isinstance(info, dict):
            continue
        env = info.get("environment", "-")
        host = info.get("host", "-")
        rows.append(f"| `{name}` | {env} | {host} |")
    if not rows:
        return "_No infrastructure configured._\n"
    header = "| Server | Environment | Host |\n"
    header += "|--------|-------------|------|"
    return header + "\n" + "\n".join(rows) + "\n"


def inject_registries(text: str, root: Path) -> str:
    registry_dir = root / ".datacore" / "registry"
    modules_dir = root / ".datacore" / "modules"

    def repl(m: re.Match) -> str:
        key = m.group(1)
        if key == "modules":
            return _generate_modules_table(modules_dir)
        elif key == "agents":
            return _generate_agents_table(registry_dir / "agents.yaml")
        elif key == "commands":
            return _generate_commands_table(registry_dir / "commands.yaml")
        elif key == "sources":
            return _generate_sources_table(registry_dir / "sources.yaml")
        elif key == "infrastructure":
            return _generate_infrastructure_table(registry_dir / "infrastructure.yaml")
        return f"_Unknown registry: {key}_\n"

    return REGISTRY_MARKER.sub(repl, text)


def merge_layers(stem: str, directory: Path) -> str:
    parts = []
    for suffix, label in LAYERS:
        path = directory / f"{stem}.{suffix}.md"
        if path.exists():
            text = path.read_text()
            parts.append(f"\n<!-- LAYER: {label} ({path.name}) -->\n\n{text}")
    return "\n".join(parts).strip()


def validate_public_layer(text: str, path: Path) -> list[str]:
    issues = []
    for pattern, desc in PRIVATE_PATTERNS:
        for m in re.finditer(pattern, text):
            line = text[:m.start()].count("\n") + 1
            issues.append(f"  {path}:{line}: potential {desc}: {m.group()!r}")
    return issues


def find_context_files(root: Path) -> list[Path]:
    files = []
    for pattern in ("CLAUDE", "SCAFFOLDING"):
        for p in root.rglob(f"{pattern}.base.md"):
            files.append(p)
    return files


def rebuild(root: Path, strict: bool = False) -> int:
    errors = 0
    for base_path in find_context_files(root):
        stem = base_path.stem.replace(".base", "")
        directory = base_path.parent
        composed_path = directory / f"{stem}.md"
        merged = merge_layers(stem, directory)
        if not merged:
            print(f"skip  {base_path} (no layers found)")
            continue

        merged = inject_registries(merged, root)

        base_text = base_path.read_text() if base_path.exists() else ""
        issues = validate_public_layer(base_text, base_path)
        if issues:
            print(f"WARN  {base_path} — private content in PUBLIC layer:")
            for issue in issues:
                print(issue)
            if strict:
                errors += 1
                continue

        composed_path.write_text(merged)
        print(f"build {composed_path}")

    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description="Merge layered context files")
    parser.add_argument("action", choices=["rebuild", "validate"])
    parser.add_argument("--path", default=".", help="Root directory")
    parser.add_argument("--strict", action="store_true", help="Fail on validation issues")
    args = parser.parse_args(argv)

    root = Path(args.path).expanduser().resolve()

    if args.action == "rebuild":
        errors = rebuild(root, strict=args.strict)
        if errors:
            print(f"\n{errors} validation error(s) — fix before committing.")
            sys.exit(1)
        print("\nDone.")
    elif args.action == "validate":
        errors = 0
        for base_path in find_context_files(root):
            base_text = base_path.read_text() if base_path.exists() else ""
            issues = validate_public_layer(base_text, base_path)
            if issues:
                print(f"{base_path}:")
                for issue in issues:
                    print(issue)
                errors += 1
        if errors:
            print(f"\n{errors} file(s) with validation issues.")
            sys.exit(1)
        print("All PUBLIC layers clean.")


if __name__ == "__main__":
    main()
