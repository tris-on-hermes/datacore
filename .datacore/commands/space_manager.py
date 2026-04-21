#!/usr/bin/env python3
"""Manage datacore team spaces.

Add, list, and remove team spaces with proper git remote setup.

Usage:
    python3 space_manager.py list
    python3 space_manager.py add <repo-url> [local-name] [--upstream <url>]
    python3 space_manager.py remove <local-name>
    python3 space_manager.py init <name> [--template <url>]
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

DATA_ROOT = Path.home() / "Data"


def run(cmd, cwd=None, check=False):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)
    return result


def list_spaces():
    spaces = []
    for entry in sorted(DATA_ROOT.iterdir()):
        if not entry.is_dir():
            continue
        git_dir = entry / ".git"
        if git_dir.exists():
            remotes = {}
            r = run(["git", "remote", "-v"], cwd=entry)
            for line in r.stdout.strip().splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    remotes[parts[0]] = parts[1]
            branch = run(["git", "branch", "--show-current"], cwd=entry).stdout.strip()
            status = run(["git", "status", "--short"], cwd=entry).stdout.strip()
            spaces.append({
                "name": entry.name,
                "path": str(entry),
                "branch": branch,
                "remotes": remotes,
                "dirty": bool(status),
            })
    return spaces


def add_space(repo_url: str, local_name: str = None, upstream_url: str = None):
    """Clone a new team space."""
    if local_name is None:
        local_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")

    target = DATA_ROOT / local_name
    if target.exists():
        print(f"Error: {target} already exists", file=sys.stderr)
        sys.exit(1)

    print(f"Cloning {repo_url} into {target}...")
    r = run(["git", "clone", repo_url, str(target)], check=True)
    if r.returncode != 0:
        print(f"Clone failed: {r.stderr}", file=sys.stderr)
        sys.exit(1)

    # If upstream URL provided, rename origin to upstream and add origin as fork
    if upstream_url:
        run(["git", "remote", "rename", "origin", "upstream"], cwd=target, check=True)
        run(["git", "remote", "add", "origin", repo_url], cwd=target, check=True)
        run(["git", "remote", "set-url", "upstream", upstream_url], cwd=target, check=True)
        print(f"Remotes configured: origin={repo_url}, upstream={upstream_url}")
    else:
        # Try to infer upstream from a GitHub fork relationship
        remotes = get_remotes(target)
        if "origin" in remotes:
            origin_url = remotes["origin"]
            # If origin is a personal fork, try to set upstream to the parent org
            if "github.com" in origin_url:
                # Simple heuristic: replace user/org with datacore-one if it looks like a fork
                parts = origin_url.split("/")
                if len(parts) >= 2:
                    # Check if repo name suggests it's a datacore space
                    repo_name = parts[-1].replace(".git", "")
                    if repo_name.startswith("datacore-"):
                        upstream_candidate = f"https://github.com/datacore-one/{repo_name}.git"
                        run(["git", "remote", "add", "upstream", upstream_candidate], cwd=target)
                        print(f"Inferred upstream: {upstream_candidate}")

    print(f"Space '{local_name}' added successfully.")
    return target


def remove_space(local_name: str, force: bool = False):
    target = DATA_ROOT / local_name
    if not target.exists():
        print(f"Error: {target} does not exist", file=sys.stderr)
        sys.exit(1)

    if (target / ".git").exists():
        # Safety check: ensure it's not the root datacore repo
        if target == DATA_ROOT:
            print("Error: Cannot remove the root ~/Data directory", file=sys.stderr)
            sys.exit(1)

        # Check for uncommitted changes
        r = run(["git", "status", "--short"], cwd=target)
        if r.stdout.strip() and not force:
            print(f"Error: {local_name} has uncommitted changes. Use --force to remove anyway.", file=sys.stderr)
            sys.exit(1)

    shutil.rmtree(target)
    print(f"Space '{local_name}' removed.")


def init_space(name: str, template_url: str = None):
    """Initialize a new local space (like 0-personal)."""
    target = DATA_ROOT / name
    if target.exists():
        print(f"Error: {target} already exists", file=sys.stderr)
        sys.exit(1)

    target.mkdir(parents=True)

    if template_url:
        print(f"Cloning template from {template_url}...")
        r = run(["git", "clone", template_url, str(target)])
        if r.returncode != 0:
            print(f"Clone failed: {r.stderr}", file=sys.stderr)
            sys.exit(1)
    else:
        # Initialize empty git repo
        run(["git", "init"], cwd=target, check=True)
        # Create basic structure
        (target / "org").mkdir()
        (target / "journal").mkdir()
        (target / "0-inbox").mkdir()
        (target / "1-tracks").mkdir()
        (target / "3-knowledge").mkdir()
        (target / "4-archive").mkdir()

    print(f"Space '{name}' initialized at {target}")


def get_remotes(space_dir: Path):
    r = run(["git", "remote", "-v"], cwd=space_dir)
    remotes = {}
    for line in r.stdout.strip().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            remotes[parts[0]] = parts[1]
    return remotes


def main():
    parser = argparse.ArgumentParser(description="Manage datacore team spaces")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    list_parser = subparsers.add_parser("list", help="List all spaces")

    # add
    add_parser = subparsers.add_parser("add", help="Add a space from a git repo")
    add_parser.add_argument("repo_url", help="Git repository URL")
    add_parser.add_argument("local_name", nargs="?", help="Local directory name (defaults to repo name)")
    add_parser.add_argument("--upstream", help="Upstream repository URL")

    # remove
    remove_parser = subparsers.add_parser("remove", help="Remove a space")
    remove_parser.add_argument("local_name", help="Local directory name")
    remove_parser.add_argument("--force", action="store_true", help="Remove even with uncommitted changes")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize a new local space")
    init_parser.add_argument("name", help="Space name (e.g., 1-my-team)")
    init_parser.add_argument("--template", help="Template repo URL to clone")

    args = parser.parse_args()

    if args.command == "list":
        spaces = list_spaces()
        if not spaces:
            print("No git-managed spaces found.")
            sys.exit(0)
        print(f"{'Space':<20} {'Branch':<12} {'Remotes':<30} {'Status'}")
        print("-" * 70)
        for s in spaces:
            remote_list = ", ".join(s["remotes"].keys())
            status = "dirty" if s["dirty"] else "clean"
            print(f"{s['name']:<20} {s['branch']:<12} {remote_list:<30} {status}")

    elif args.command == "add":
        add_space(args.repo_url, args.local_name, args.upstream)

    elif args.command == "remove":
        remove_space(args.local_name, args.force)

    elif args.command == "init":
        init_space(args.name, args.template)


if __name__ == "__main__":
    main()
