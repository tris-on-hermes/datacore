#!/usr/bin/env python3
"""Lightweight org-mode parser for Datacore GTD operations.

Handles basic task querying and manipulation without the full org_workspace
dependency. Install org_workspace for advanced features.

Usage:
    python3 org_parser.py count ~/Data/0-personal/org/inbox.org
    python3 org_parser.py list ~/Data/0-personal/org/next_actions.org --states TODO,NEXT --tags AI
    python3 org_parser.py add ~/Data/0-personal/org/inbox.org "Review quarterly report" --tags AI:research
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

TODO_RE = re.compile(r'^(\*+)\s+(TODO|NEXT|WAITING|DONE|CANCELLED)?\s*(?:\[#([A-C])\])?\s*(.*?)(?:\s+:(.+):)?\s*$')
PROP_RE = re.compile(r'^\s*:([A-Z_]+):\s*(.*)$')
SCHED_RE = re.compile(r'(SCHEDULED|DEADLINE|CLOSED):\s*<(\d{4}-\d{2}-\d{2})\s+\w{3}(?:\s+\d{2}:\d{2})?>'
)


class OrgNode:
    def __init__(self, level: int, state: Optional[str], priority: Optional[str],
                 heading: str, tags: list[str], line_no: int):
        self.level = level
        self.state = state
        self.priority = priority
        self.heading = heading
        self.tags = tags
        self.line_no = line_no
        self.properties: dict[str, str] = {}
        self.scheduled: Optional[str] = None
        self.deadline: Optional[str] = None
        self.closed: Optional[str] = None
        self.body_lines: list[str] = []

    def to_dict(self) -> dict:
        return {
            "line": self.line_no,
            "level": self.level,
            "state": self.state,
            "priority": self.priority,
            "heading": self.heading,
            "tags": self.tags,
            "properties": self.properties,
            "scheduled": self.scheduled,
            "deadline": self.deadline,
            "closed": self.closed,
        }


def parse_org(path: Path) -> list[OrgNode]:
    text = path.read_text()
    nodes: list[OrgNode] = []
    current: Optional[OrgNode] = None
    in_properties = False

    for i, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.rstrip()
        m = TODO_RE.match(line)
        if m:
            level = len(m.group(1))
            state = m.group(2)
            priority = m.group(3)
            heading = m.group(4).strip()
            tags_str = m.group(5)
            tags = [t.strip() for t in tags_str.split(":") if t.strip()] if tags_str else []
            current = OrgNode(level, state, priority, heading, tags, i)
            nodes.append(current)
            in_properties = False
            continue

        if current is None:
            continue

        if line.strip() == ":PROPERTIES:":
            in_properties = True
            continue
        if line.strip() == ":END:":
            in_properties = False
            continue

        pm = PROP_RE.match(line)
        if pm and in_properties:
            current.properties[pm.group(1)] = pm.group(2)
            continue

        sm = SCHED_RE.search(line)
        if sm:
            key = sm.group(1).lower()
            val = sm.group(2)
            setattr(current, key, val)
            continue

        if line.strip():
            current.body_lines.append(line)

    return nodes


def cmd_count(args):
    nodes = parse_org(Path(args.file))
    terminal = {"DONE", "CANCELLED"}
    count = sum(1 for n in nodes if n.state and n.state not in terminal)
    print(json.dumps({"count": count, "file": args.file}))


def cmd_list(args):
    nodes = parse_org(Path(args.file))
    states = [s.strip() for s in args.states.split(",")] if args.states else None
    tags = [t.strip().strip(":") for t in args.tags.split(",")] if args.tags else None
    results = []
    for n in nodes:
        if states and n.state not in states:
            continue
        if tags:
            if not any(t in n.tags for t in tags):
                continue
        results.append(n.to_dict())
        if args.limit and len(results) >= args.limit:
            break
    print(json.dumps({"count": len(results), "tasks": results}, indent=2))


def cmd_add(args):
    path = Path(args.file)
    path.parent.mkdir(parents=True, exist_ok=True)

    tags = []
    if args.tags:
        raw = args.tags.strip(":")
        tags = [t for t in raw.replace(",", ":").split(":") if t]
    tag_str = f" :{':'.join(tags)}:" if tags else ""

    priority_str = f" [#{args.priority}]" if args.priority else ""
    state_str = args.state or "TODO"

    lines = [f"* {state_str}{priority_str} {args.heading}{tag_str}"]

    now = datetime.now()
    wday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][now.weekday()]
    created = f"[{now.strftime('%Y-%m-%d')} {wday} {now.strftime('%H:%M')}]"

    props = {"CREATED": created}
    if args.property:
        for p in args.property:
            if "=" in p:
                k, v = p.split("=", 1)
                props[k] = v

    if props:
        lines.append(":PROPERTIES:")
        for k, v in props.items():
            lines.append(f":{k}: {v}")
        lines.append(":END:")

    if args.scheduled:
        from date_utils import dow
        day = dow(args.scheduled)
        lines.append(f"SCHEDULED: <{args.scheduled} {day}>")

    if args.body:
        lines.append(args.body)

    lines.append("")

    if path.exists():
        text = path.read_text()
        if text and not text.endswith("\n"):
            text += "\n"
        text += "\n".join(lines) + "\n"
    else:
        text = "\n".join(lines) + "\n"

    path.write_text(text)
    print(json.dumps({"ok": True, "file": str(path), "heading": args.heading}))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Lightweight org-mode parser")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("count", help="Count active tasks")
    p.add_argument("file")

    p = sub.add_parser("list", help="List tasks with filters")
    p.add_argument("file")
    p.add_argument("--states")
    p.add_argument("--tags")
    p.add_argument("--limit", type=int)

    p = sub.add_parser("add", help="Add a task")
    p.add_argument("file")
    p.add_argument("heading")
    p.add_argument("--state", default="TODO")
    p.add_argument("--priority")
    p.add_argument("--tags")
    p.add_argument("--scheduled")
    p.add_argument("--property", action="append")
    p.add_argument("--body")

    args = parser.parse_args(argv)
    if args.cmd == "count":
        cmd_count(args)
    elif args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "add":
        cmd_add(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
