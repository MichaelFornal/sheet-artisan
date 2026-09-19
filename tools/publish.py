"""Stage, gate and (only with --go) publish a run's pipe.

    ./sa publish <slug> --tier public|private|none [--name repo-name] [--zip] [--go]

Without --go nothing leaves the machine: the staged copy lands in runs/<slug>/publish/<tier>/ for
review and the plan is printed. --go is given only after Mike says go in B5.

public   github.com/<owner>/<niche-slug>, public. Sources flagged `private` are removed (code and
         spec entry), the target company's name and domain may not appear anywhere, contacts fail.
private  same repo name, private, full pipe. Mike invites the recipient by email in the GitHub UI;
         guests on a personal-account repo always get write access.
none     no GitHub. --zip writes the scanned pipe to out/<name>-pipe.zip for the package.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.common import ALLOWED_TIERS, TIERS, append_log, config, load_run, now, save_run  # noqa: E402
from tools.scan import report, scan  # noqa: E402

SAMPLE_ROWS = 25


def _files(pipe):
    out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=pipe, check=True,
                         capture_output=True, text=True).stdout.split("\n")
    return [f for f in out if f and (pipe / f).is_file()]


def stage(slug, tier, name=None, runs=None):
    """Build the staged copy and gate it. Returns a plan dict; raises SystemExit on refusal."""
    cfg = config()
    path, run = load_run(slug, runs)
    pipe = path / "pipe"
    spec = json.loads((pipe / "spec.json").read_text())
    sensitivity = spec.get("sensitivity")
    if tier not in ALLOWED_TIERS.get(sensitivity, set()):
        raise SystemExit(f"refused: sensitivity {sensitivity!r} allows only "
                         f"{sorted(ALLOWED_TIERS.get(sensitivity, []))}, not {tier!r}")
    name = name or spec.get("niche_slug")
    if not name or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,80}", name):
        raise SystemExit(f"refused: repo name {name!r} must be a lower-case niche slug")
    if tier == "public" and any(t.lower() in name.lower() for t in run.get("deny_terms", []) if t):
        raise SystemExit("refused: a public repo may not be named after the target company")

    dest = path / "publish" / tier
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for rel in _files(pipe):
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pipe / rel, dest / rel)

    stripped = []
    staged_spec = json.loads((dest / "spec.json").read_text())
    if tier == "public":
        for s in staged_spec.get("sources", []):
            if s.get("publish") == "private":
                mod = dest / "src" / "sources" / f"{s['name']}.py"
                if mod.exists():
                    mod.unlink()
                stripped.append(s["name"])
                s.clear()
                s.update({"name": stripped[-1], "publish": "private", "withheld": True,
                          "url": "withheld", "method": "withheld",
                          "notes": "Collection method not published; the rest of the pipe runs without it."})
    repo_url = f"https://github.com/{cfg['github_owner']}/{name}" if tier != "none" else None
    staged_spec["repo_url"] = repo_url
    (dest / "spec.json").write_text(json.dumps(staged_spec, indent=2) + "\n")

    rows_p = next((p for p in (pipe / "data" / "rows.full.jsonl", pipe / "data" / "rows.sample.jsonl")
                   if p.exists()), None)
    sample_n = 0
    if rows_p:
        cols = [c["name"] for c in spec.get("columns", [])]
        (dest / "sample").mkdir(exist_ok=True)
        with rows_p.open() as fh, (dest / "sample" / "sample_rows.csv").open("w", newline="") as out:
            w = csv.DictWriter(out, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for line in fh:
                row = json.loads(line)
                if row.get("_source") in stripped:
                    continue
                w.writerow({c: row.get(c) for c in cols})
                sample_n += 1
                if sample_n >= SAMPLE_ROWS:
                    break

    if not (dest / "README.md").exists():
        raise SystemExit("refused: no README.md in the pipe; run `make readme` after writing README.tmpl.md")

    deny = run.get("deny_terms", []) if tier == "public" else []
    result = scan(dest, deny=deny, strict_contacts=(tier == "public"))
    return {"slug": slug, "tier": tier, "name": name, "repo_url": repo_url, "dest": dest,
            "files": sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file()),
            "stripped": stripped, "sample_rows": sample_n, "scan": result, "title": spec.get("title"),
            "path": path, "run": run, "cfg": cfg}


def print_plan(plan):
    print(f"tier:      {plan['tier']}")
    print(f"repo:      {plan['repo_url'] or '(none: not published to GitHub)'}")
    print(f"staged:    {plan['dest']}  ({len(plan['files'])} files)")
    print(f"withheld:  {', '.join(plan['stripped']) or 'nothing'}")
    print(f"sample:    {plan['sample_rows']} rows in sample/sample_rows.csv")
    report(plan["scan"])
    if plan["tier"] == "private":
        print("after publishing: invite the recipient by email at "
              f"{plan['repo_url']}/settings/access (they will get write access)")


def go(plan, make_zip=False, runner=subprocess.run):
    dest, cfg, tier = plan["dest"], plan["cfg"], plan["tier"]
    if tier == "none":
        if make_zip:
            zpath = plan["path"] / "out" / f"{plan['name']}-pipe.zip"
            with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
                for rel in plan["files"]:
                    z.write(dest / rel, f"{plan['name']}/{rel}")
            print(f"wrote {zpath}")
            return str(zpath)
        print("tier none: nothing to publish")
        return None
    owner_repo = f"{cfg['github_owner']}/{plan['name']}"
    exists = runner(["gh", "repo", "view", owner_repo], capture_output=True, text=True)
    if exists.returncode == 0:
        raise SystemExit(f"refused: {owner_repo} already exists; pick --name or update it by hand")
    ident = ["-c", f"user.name={cfg['git_name']}", "-c", f"user.email={cfg['git_email']}"]
    message = f"{plan['title']}\n\n{cfg.get('commit_trailer', '')}".strip()
    for cmd in (["git", "init", "-q", "-b", "main"], ["git", "add", "-A"],
                ["git", *ident, "commit", "-q", "-m", message]):
        runner(cmd, cwd=dest, check=True)
    runner(["gh", "repo", "create", owner_repo, f"--{tier}", "--source", ".", "--push",
            "--description", plan["title"] or plan["name"]], cwd=dest, check=True)
    return plan["repo_url"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--tier", choices=TIERS, required=True)
    ap.add_argument("--name")
    ap.add_argument("--zip", action="store_true")
    ap.add_argument("--go", action="store_true", help="actually publish (only after Mike says go)")
    ap.add_argument("--runs-dir")
    args = ap.parse_args()
    plan = stage(args.slug, args.tier, args.name, args.runs_dir)
    print_plan(plan)
    if plan["scan"]["fail"]:
        raise SystemExit("refused: the scan failed; fix the files above and re-run")
    if not args.go:
        print("dry run: nothing left this machine. Re-run with --go once Mike says go.")
        return
    where = go(plan, args.zip)
    run = plan["run"]
    run["published"] = {"tier": args.tier, "where": where, "at": now()}
    save_run(plan["path"], run)
    append_log(plan["path"], run["stage"], f"published ({args.tier}): {where}")
    print(f"published: {where}")


if __name__ == "__main__":
    main()
