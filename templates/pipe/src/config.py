"""Paths and settings every stage of the pipe shares."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "spec.json").read_text())

DATA = ROOT / "data"
CACHE = DATA / "cache"
LLM_CACHE = DATA / "llm_cache"

MODE = os.environ.get("MODE", "sample")
SAMPLE_N = int(os.environ.get("SAMPLE_N", "25"))
OFFLINE = os.environ.get("OFFLINE") == "1"

# Inside a Sheet Artisan run the pipe sits next to package/ (company-specific, never published).
PACKAGE = Path(os.environ["PACKAGE"]) if os.environ.get("PACKAGE") else ROOT.parent / "package"
IN_RUN = (PACKAGE / "package.json").exists()
OUT = Path(os.environ["OUT_DIR"]) if os.environ.get("OUT_DIR") else (ROOT.parent / "out" if IN_RUN else ROOT / "out")

USER_AGENT = SPEC.get("user_agent") or "sheet-artisan-pipe/0.1"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def fetcher():
    from kit.fetch import Fetcher
    return Fetcher(CACHE, user_agent=USER_AGENT, rate=SPEC.get("rate", 1.0), offline=OFFLINE)


def llm():
    from kit.llm import LLM
    return LLM(LLM_CACHE, offline=OFFLINE)


def package():
    """Run-only details (company, contact, file name). Empty in a published clone."""
    return json.loads((PACKAGE / "package.json").read_text()) if IN_RUN else {}


def rows_path(mode=None):
    return DATA / f"rows.{mode or MODE}.jsonl"


def load_rows(mode=None):
    path = rows_path(mode)
    if not path.exists():
        raise SystemExit(f"{path.name} not found: run `make {'full' if (mode or MODE) == 'full' else 'sample'}` first")
    with path.open() as fh:
        return [json.loads(line) for line in fh if line.strip()]
