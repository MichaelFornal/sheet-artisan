"""Shared helpers for the Sheet Artisan tools."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = ["kickoff", "b1", "b2", "b3", "build", "sample-check", "crawl", "qa", "b4", "package",
          "b5", "retro", "done"]
TIERS = ("public", "private", "none")
# Which sharing tiers each sensitivity level allows (docs/design.md, "Sharing tiers").
ALLOWED_TIERS = {"none": {"public", "private", "none"}, "personal": {"private", "none"},
                 "outreach": {"private", "none"}, "sensitive": {"private", "none"}}


def config():
    return json.loads((ROOT / "config.json").read_text())


def runs_dir(override=None):
    return Path(override or os.environ.get("SA_RUNS_DIR") or ROOT / "runs")


def slugify(text):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def run_path(slug, override=None):
    p = runs_dir(override) / slug
    if not (p / "run.json").exists():
        raise SystemExit(f"no run named {slug!r} in {runs_dir(override)}")
    return p


def load_run(slug, override=None):
    p = run_path(slug, override)
    return p, json.loads((p / "run.json").read_text())


def save_run(path, run):
    (path / "run.json").write_text(json.dumps(run, indent=2) + "\n")


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def append_log(path, stage, note):
    md = path / "run.md"
    text = md.read_text() if md.exists() else "# Run\n\n## Log\n"
    if "## Log" not in text:
        text += "\n## Log\n"
    md.write_text(text.rstrip("\n") + f"\n- {now()} · {stage} · {note}\n")
