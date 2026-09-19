"""Every number in prose must be computed. Fails on any digit a template states by hand.

    python3 tools/claims_check.py FILE... [--facts out/facts.full.json]

A template may carry digits only inside {{fact:key}}, {{lit:...}} or {{var:name}} (plus dates,
URLs, code and list numbering). With --facts, every {{fact:key}} must exist in that file.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kit.facts import bare_numbers, load, placeholders  # noqa: E402


def check(paths, facts_path=None):
    """Return a list of problems as strings; empty means clean."""
    facts = load(facts_path) if facts_path and Path(facts_path).exists() else None
    problems = []
    if facts_path and facts is None:
        problems.append(f"{facts_path}: facts file not found (run `make sheet` first)")
    for p in paths:
        p = Path(p)
        if not p.exists():
            problems.append(f"{p}: missing")
            continue
        text = p.read_text()
        for line_no, line in bare_numbers(text):
            problems.append(f"{p}:{line_no}: number not backed by a fact: {line}")
        if facts is not None:
            for key in placeholders(text, "fact"):
                if key not in facts:
                    problems.append(f"{p}: {{{{fact:{key}}}}} is not defined in facts_def.py")
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--facts")
    args = ap.parse_args()
    problems = check(args.files, args.facts)
    for pr in problems:
        print(pr)
    print(f"claims: {len(problems)} problems in {len(args.files)} files")
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
