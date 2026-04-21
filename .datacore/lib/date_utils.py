#!/usr/bin/env python3
"""Canonical date operations for Datacore — Hermes Edition.

LLMs are bad at day-of-week arithmetic and anchor to training-era dates.
This module is the single source of truth for any date operation.

CLI:
    date_utils.py today                    # 2026-04-08 Wed
    date_utils.py today --iso              # 2026-04-08
    date_utils.py today --full             # 2026-04-08 Wed 14:32
    date_utils.py dow 2026-04-08           # Wed
    date_utils.py validate 2026-04-08 Wed  # ok / mismatch
    date_utils.py add 2026-04-08 3         # 2026-04-11 Sat
    date_utils.py parse "next monday"      # resolved against today
    date_utils.py org-stamp 2026-04-08     # <2026-04-08 Wed>
    date_utils.py fix "2026-04-08 Tue foo" # 2026-04-08 Wed foo

Library:
    from date_utils import today, dow, validate, add_days, org_stamp
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, timedelta
from typing import Optional

DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
DATE_DOW_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\s+(Mon|Tue|Wed|Thu|Fri|Sat|Sun)")
DOWS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _parse_iso(s: str) -> date:
    m = DATE_RE.match(s)
    if not m:
        raise ValueError(f"not a YYYY-MM-DD date: {s!r}")
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def today() -> date:
    return date.today()


def dow(d: str | date) -> str:
    if isinstance(d, str):
        d = _parse_iso(d)
    return d.strftime("%a")


def validate(d: str, day_name: str) -> bool:
    return dow(d) == day_name


def add_days(d: str | date, n: int) -> date:
    if isinstance(d, str):
        d = _parse_iso(d)
    return d + timedelta(days=n)


def diff_days(a: str | date, b: str | date) -> int:
    if isinstance(a, str):
        a = _parse_iso(a)
    if isinstance(b, str):
        b = _parse_iso(b)
    return (b - a).days


def org_stamp(d: str | date, inactive: bool = False) -> str:
    if isinstance(d, str):
        d = _parse_iso(d)
    stamp = f"{d.isoformat()} {d.strftime('%a')}"
    return f"[{stamp}]" if inactive else f"<{stamp}>"


def parse_relative(expr: str, base: Optional[date] = None) -> date:
    if base is None:
        base = today()
    s = expr.strip().lower()
    if DATE_RE.match(s):
        return _parse_iso(s[:10])
    if s == "today":
        return base
    if s == "tomorrow":
        return base + timedelta(days=1)
    if s == "yesterday":
        return base - timedelta(days=1)
    m = re.match(r"in\s+(\d+)\s+days?", s)
    if m:
        return base + timedelta(days=int(m.group(1)))
    m = re.match(r"(\d+)\s+days?\s+ago", s)
    if m:
        return base - timedelta(days=int(m.group(1)))
    m = re.match(r"(next|last)\s+(mon|tue|wed|thu|fri|sat|sun)", s)
    if m:
        direction = 1 if m.group(1) == "next" else -1
        target = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"].index(m.group(2))
        delta = (target - base.weekday()) % 7
        if delta == 0:
            delta = 7
        return base + timedelta(days=delta * direction if direction > 0 else -((7 - delta) % 7 or 7))
    if s == "next week":
        return base + timedelta(days=7)
    if s == "last week":
        return base - timedelta(days=7)
    raise ValueError(f"cannot parse relative date: {expr!r}")


def fix_day_names(text: str) -> tuple[str, int]:
    fixes = 0
    def repl(m: re.Match) -> str:
        nonlocal fixes
        date_str, day_name = m.group(1), m.group(2)
        try:
            actual = dow(date_str)
            if actual != day_name:
                fixes += 1
                return f"{date_str} {actual}"
        except ValueError:
            pass
        return m.group(0)
    return DATE_DOW_RE.sub(repl, text), fixes


def find_mismatches(text: str) -> list[dict]:
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in DATE_DOW_RE.finditer(line):
            date_str, claimed = m.group(1), m.group(2)
            try:
                actual = dow(date_str)
                if actual != claimed:
                    out.append({"date": date_str, "claimed": claimed, "actual": actual, "line": i})
            except ValueError:
                pass
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Canonical date operations")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("today", help="Today's date")
    p.add_argument("--iso", action="store_true")
    p.add_argument("--full", action="store_true")

    p = sub.add_parser("dow", help="Day of week for date")
    p.add_argument("date")

    p = sub.add_parser("validate", help="Validate date+day match")
    p.add_argument("date")
    p.add_argument("day")

    p = sub.add_parser("add", help="Add N days")
    p.add_argument("date")
    p.add_argument("days", type=int)

    p = sub.add_parser("sub", help="Subtract N days")
    p.add_argument("date")
    p.add_argument("days", type=int)

    p = sub.add_parser("diff", help="Difference in days")
    p.add_argument("a")
    p.add_argument("b")

    p = sub.add_parser("parse", help="Parse relative date")
    p.add_argument("expr")

    p = sub.add_parser("org-stamp", help="Format org timestamp")
    p.add_argument("date")
    p.add_argument("--inactive", action="store_true")

    p = sub.add_parser("fix", help="Fix day names in text")
    p.add_argument("text")

    args = parser.parse_args(argv)

    if args.cmd == "today":
        d = today()
        if args.full:
            print(f"{d.isoformat()} {d.strftime('%a')} {datetime.now().strftime('%H:%M')}")
        elif args.iso:
            print(d.isoformat())
        else:
            print(f"{d.isoformat()} {d.strftime('%a')}")
    elif args.cmd == "dow":
        print(dow(args.date))
    elif args.cmd == "validate":
        ok = validate(args.date, args.day)
        print("ok" if ok else f"mismatch: {args.date} is {dow(args.date)}, not {args.day}")
        sys.exit(0 if ok else 1)
    elif args.cmd == "add":
        print(add_days(args.date, args.days).isoformat())
    elif args.cmd == "sub":
        print(add_days(args.date, -args.days).isoformat())
    elif args.cmd == "diff":
        print(diff_days(args.a, args.b))
    elif args.cmd == "parse":
        print(parse_relative(args.expr).isoformat())
    elif args.cmd == "org-stamp":
        print(org_stamp(args.date, inactive=args.inactive))
    elif args.cmd == "fix":
        fixed, n = fix_day_names(args.text)
        print(fixed)
        if n:
            print(f"# fixed {n} mismatch(es)", file=sys.stderr)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
