"""Move a run to a stage, count searches, record decisions, or show where every run stands.

    ./sa status                         every run, its stage and search spend
    ./sa status <slug>                  one run in detail (what to do next)
    ./sa stage <slug> <stage> "note"    advance (stages: kickoff b1 b2 b3 build sample-check crawl
                                        qa b4 package b5 retro done)
    ./sa search <slug> <b1|b2|b3|reserve> [N]   count N WebSearch calls (default 1)
    ./sa decide <slug> <key> "value"    record a brainstorm decision (also logged to run.md)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.common import STAGES, append_log, load_run, runs_dir, save_run  # noqa: E402

BUDGET = {"b1": 30, "b2": 30, "b3": 60, "reserve": 40}
GUIDE = {"kickoff": "b1-company.md", "b1": "b1-company.md", "b2": "b2-ideation.md", "b3": "b3-sources.md",
         "build": "build.md", "sample-check": "sample-check.md", "crawl": "crawl.md", "qa": "qa.md",
         "b4": "b4-insights.md", "package": "package.md", "b5": "b5-ship.md", "retro": "retro.md",
         "done": "retro.md"}


def status(slug=None, runs=None):
    if slug:
        path, run = load_run(slug, runs)
        spent = sum(run["searches"].values())
        print(f"{run['company']}  ({slug})  stage: {run['stage']}  searches: {spent}/200")
        for k, v in run["searches"].items():
            print(f"  {k:8} {v:>3}/{BUDGET.get(k, '?')}")
        for k, v in run.get("decisions", {}).items():
            print(f"  decided {k}: {v}")
        if run.get("published"):
            print(f"  published: {run['published']}")
        print(f"  guide: playbook/{GUIDE.get(run['stage'], 'README')}")
        return
    rows = []
    for p in sorted(runs_dir(runs).glob("*/run.json")):
        run = json.loads(p.read_text())
        rows.append((run["slug"], run["company"], run["stage"], sum(run["searches"].values())))
    if not rows:
        print("no runs yet: ./sa new \"Company\" [--posting URL]")
    for slug_, company, stage, spent in rows:
        print(f"{slug_:28} {stage:13} searches {spent:>3}/200  {company}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--runs-dir")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status", parents=[common])
    s.add_argument("slug", nargs="?")
    s = sub.add_parser("stage", parents=[common])
    s.add_argument("slug")
    s.add_argument("stage", choices=STAGES)
    s.add_argument("note", nargs="?", default="")
    s = sub.add_parser("search", parents=[common])
    s.add_argument("slug")
    s.add_argument("bucket", choices=list(BUDGET))
    s.add_argument("n", nargs="?", type=int, default=1)
    s = sub.add_parser("decide", parents=[common])
    s.add_argument("slug")
    s.add_argument("key")
    s.add_argument("value")
    args = ap.parse_args()

    if args.cmd == "status":
        return status(args.slug, args.runs_dir)
    path, run = load_run(args.slug, args.runs_dir)
    if args.cmd == "stage":
        run["stage"] = args.stage
        append_log(path, args.stage, args.note or "stage started")
        print(f"{args.slug}: now at {args.stage} -> playbook/{GUIDE[args.stage]}")
    elif args.cmd == "search":
        run["searches"][args.bucket] = run["searches"].get(args.bucket, 0) + args.n
        used, cap = run["searches"][args.bucket], BUDGET[args.bucket]
        total = sum(run["searches"].values())
        print(f"{args.bucket}: {used}/{cap} · session total {total}/200")
        if used > cap:
            print(f"OVER the {args.bucket} budget: switch to WebFetch on known URLs")
    elif args.cmd == "decide":
        run.setdefault("decisions", {})[args.key] = args.value
        append_log(path, run["stage"], f"decided {args.key}: {args.value}")
        print(f"recorded {args.key}")
    save_run(path, run)


if __name__ == "__main__":
    main()
