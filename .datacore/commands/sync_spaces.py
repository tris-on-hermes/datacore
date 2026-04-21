#!/usr/bin/env python3
"""Sync all team spaces under ~/Data.

Fetches upstream for each git-managed space and reports status.
Can optionally auto-merge upstream changes when safe.

Usage:
    python3 sync_spaces.py
    python3 sync_spaces.py --auto-merge
    python3 sync_spaces.py --fetch-only
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run(cmd, cwd, check=False):
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, check=check
    )
    return result


def discover_spaces(root: Path):
    """Find all git repos directly under root."""
    spaces = []
    for entry in sorted(root.iterdir()):
        if entry.is_dir() and (entry / ".git").exists():
            spaces.append(entry)
    # Also include root itself if it's a git repo
    if (root / ".git").exists():
        spaces.insert(0, root)
    return spaces


def get_remotes(space_dir: Path):
    r = run(["git", "remote", "-v"], cwd=space_dir)
    remotes = {}
    for line in r.stdout.strip().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            remotes[parts[0]] = parts[1]
    return remotes


def get_branch(space_dir: Path):
    r = run(["git", "branch", "--show-current"], cwd=space_dir)
    return r.stdout.strip()


def fetch_remote(space_dir: Path, remote: str):
    r = run(["git", "fetch", remote], cwd=space_dir)
    return r.returncode == 0, r.stderr.strip()


def compare_branch(space_dir: Path, local_branch: str, remote_ref: str):
    """Returns (ahead, behind) commit counts."""
    r = run(
        ["git", "rev-list", "--left-right", "--count", f"{remote_ref}...{local_branch}"],
        cwd=space_dir,
    )
    if r.returncode != 0:
        return None, None
    try:
        behind, ahead = map(int, r.stdout.strip().split())
        return ahead, behind
    except ValueError:
        return None, None


def has_uncommitted_changes(space_dir: Path):
    r = run(["git", "status", "--porcelain"], cwd=space_dir)
    return bool(r.stdout.strip())


def merge_remote(space_dir: Path, remote: str, branch: str):
    r = run(["git", "merge", "--ff-only", f"{remote}/{branch}"], cwd=space_dir)
    return r.returncode == 0, r.stderr.strip() or r.stdout.strip()


def sync_space(space_dir: Path, auto_merge: bool = False, fetch_only: bool = False):
    name = space_dir.name if space_dir != Path.home() / "Data" else "(root)"
    remotes = get_remotes(space_dir)
    branch = get_branch(space_dir)

    # Determine which remote to sync from
    sync_remote = None
    if "upstream" in remotes:
        sync_remote = "upstream"
    elif "origin" in remotes:
        sync_remote = "origin"

    if not sync_remote:
        return {
            "name": name,
            "path": str(space_dir),
            "branch": branch,
            "status": "no_remote",
            "detail": "No upstream or origin remote configured",
        }

    # Fetch
    ok, err = fetch_remote(space_dir, sync_remote)
    if not ok:
        return {
            "name": name,
            "path": str(space_dir),
            "branch": branch,
            "status": "fetch_failed",
            "detail": err,
        }

    # Compare
    ahead, behind = compare_branch(space_dir, branch, f"{sync_remote}/{branch}")
    if ahead is None:
        return {
            "name": name,
            "path": str(space_dir),
            "branch": branch,
            "status": "diverged",
            "detail": "Cannot compare branches (possibly diverged)",
        }

    uncommitted = has_uncommitted_changes(space_dir)

    if ahead == 0 and behind == 0:
        status = "synced"
        detail = "Up to date" + (" (uncommitted changes)" if uncommitted else "")
    elif ahead > 0 and behind == 0:
        status = "ahead"
        detail = f"{ahead} commit(s) ahead of {sync_remote}"
    elif ahead == 0 and behind > 0:
        status = "behind"
        detail = f"{behind} commit(s) behind {sync_remote}"
        if auto_merge and not uncommitted:
            merged_ok, merge_err = merge_remote(space_dir, sync_remote, branch)
            if merged_ok:
                status = "merged"
                detail = f"Fast-forwarded {behind} commit(s) from {sync_remote}"
            else:
                status = "merge_failed"
                detail = merge_err
    else:
        status = "diverged"
        detail = f"{ahead} ahead, {behind} behind {sync_remote}"

    if uncommitted and status not in ("merge_failed", "fetch_failed"):
        detail += " | uncommitted changes"

    return {
        "name": name,
        "path": str(space_dir),
        "branch": branch,
        "status": status,
        "detail": detail,
        "ahead": ahead,
        "behind": behind,
        "uncommitted": uncommitted,
    }


def main():
    parser = argparse.ArgumentParser(description="Sync datacore team spaces")
    parser.add_argument("--auto-merge", action="store_true", help="Auto fast-forward when behind upstream")
    parser.add_argument("--fetch-only", action="store_true", help="Only fetch, do not report detailed comparison")
    parser.add_argument("--root", type=Path, default=Path.home() / "Data", help="Root directory to scan")
    args = parser.parse_args()

    spaces = discover_spaces(args.root)
    if not spaces:
        print("No git-managed spaces found under", args.root)
        sys.exit(0)

    results = []
    for space in spaces:
        res = sync_space(space, auto_merge=args.auto_merge, fetch_only=args.fetch_only)
        results.append(res)

    # Print summary table
    print(f"\n{'Space':<20} {'Branch':<12} {'Status':<12} {'Detail'}")
    print("-" * 70)
    for r in results:
        print(f"{r['name']:<20} {r['branch']:<12} {r['status']:<12} {r['detail']}")

    # Exit with non-zero if any failures
    failures = [r for r in results if r["status"] in ("fetch_failed", "merge_failed")]
    if failures:
        print(f"\n⚠ {len(failures)} space(s) had errors.")
        sys.exit(1)

    # Print quick stats
    synced = len([r for r in results if r["status"] == "synced"])
    behind = len([r for r in results if r["status"] == "behind"])
    ahead = len([r for r in results if r["status"] == "ahead"])
    merged = len([r for r in results if r["status"] == "merged"])
    print(f"\n✓ {synced} synced, {merged} merged, {behind} behind, {ahead} ahead")


if __name__ == "__main__":
    main()
