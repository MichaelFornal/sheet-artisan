"""Start a run: scaffold runs/<slug>/ with its stage docs, package drafts and a pipe repo.

    ./sa new "Acme Robotics" [--posting URL] [--domain acme.com] [--slug acme]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.common import ROOT, append_log, config, runs_dir, save_run, slugify  # noqa: E402

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def _fill(text, values):
    for k, v in values.items():
        text = text.replace(f"<<{k}>>", v)
    return text


def _copy_filled(src_dir, dest_dir, values):
    for src in sorted(Path(src_dir).rglob("*")):
        if src.is_dir() or "__pycache__" in src.parts:
            continue
        dest = dest_dir / src.relative_to(src_dir)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(_fill(src.read_text(), values))


LEGAL = r"[\s,]+(inc|llc|ltd|corp|corporation|co|company|gmbh|plc|pbc|lp|llp)\.?$"


def deny_terms(company, domain):
    """What a public repo must never say: the name as written, without its legal suffix, the domain.

    A company named with a common word ("Linear", "Ramp") will trip the scan on ordinary prose;
    edit run.json deny_terms to something more specific when that happens.
    """
    bare = re.sub(LEGAL, "", company.strip(), flags=re.I).strip(" ,.")
    return list(dict.fromkeys(t for t in (company.strip(), bare, domain) if t))


def git(cwd, *args, cfg):
    ident = ["-c", f"user.name={cfg['git_name']}", "-c", f"user.email={cfg['git_email']}"]
    subprocess.run(["git", *ident, *args], cwd=cwd, check=True, capture_output=True)


def scaffold(company, posting="", domain="", slug=None, runs=None):
    cfg = config()
    slug = slug or slugify(company)
    run = runs_dir(runs) / slug
    if run.exists():
        raise SystemExit(f"{run} already exists: resume it (./sa status {slug}) or pick another --slug")
    values = {
        "company": company, "slug": slug, "domain": domain or "", "posting": posting or "(none)",
        "date": date.today().isoformat(), "prefix": re.sub(r"[^A-Za-z0-9]+", "", company.title()),
        "author": cfg.get("author_line", ""),
        "contact": cfg.get("contact_line") or "REPLACE: your contact line (set contact_line in config.json)",
    }
    run.mkdir(parents=True)
    _copy_filled(ROOT / "templates" / "run", run, values)
    _copy_filled(ROOT / "templates" / "package", run / "package", values)
    (run / "out").mkdir()

    pipe = run / "pipe"
    shutil.copytree(ROOT / "templates" / "pipe", pipe, ignore=IGNORE)
    shutil.copytree(ROOT / "kit", pipe / "kit", ignore=IGNORE)
    spec_p = pipe / "spec.json"
    spec = json.loads(spec_p.read_text())
    spec["user_agent"] = f"sheet-artisan-pipe/0.1 (+https://github.com/{cfg['github_owner']})"
    spec_p.write_text(json.dumps(spec, indent=2) + "\n")
    subprocess.run(["git", "init", "-q"], cwd=pipe, check=True)
    git(pipe, "add", "-A", cfg=cfg)
    git(pipe, "commit", "-q", "-m", "Scaffold from Sheet Artisan", cfg=cfg)

    save_run(run, {
        "company": company, "slug": slug, "domain": domain or "", "posting": posting or "",
        "created": values["date"], "stage": "kickoff",
        "searches": {"b1": 0, "b2": 0, "b3": 0, "reserve": 0},
        "deny_terms": deny_terms(company, domain),
        "decisions": {}, "published": None,
    })
    append_log(run, "kickoff", f"run created for {company}" + (f" ({posting})" if posting else ""))
    return run


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("company")
    ap.add_argument("--posting", default="")
    ap.add_argument("--domain", default="")
    ap.add_argument("--slug")
    ap.add_argument("--runs-dir")
    args = ap.parse_args()
    run = scaffold(args.company, args.posting, args.domain, args.slug, args.runs_dir)
    print(f"created {run}")
    print("next: read playbook/b1-company.md and start the company read-back")


if __name__ == "__main__":
    main()
