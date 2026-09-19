"""Scan a directory before anything leaves the machine.

    python3 tools/scan.py <dir> [--deny TERM ...] [--strict-contacts]

Always fails on: credential shapes, private keys, local home paths, REPLACE markers.
Contacts (emails, phone numbers) fail with --strict-contacts (public tier), warn otherwise.
Deny terms (the target company's name and domain in the public tier) fail as whole words.
A pattern that cannot be compiled is itself a failure: a broken scanner must never read as clean.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.common import config  # noqa: E402

SECRETS = {
    "aws access key": r"\bAKIA[0-9A-Z]{16}\b",
    "github token": r"\bgh[pousr]_[A-Za-z0-9]{30,}\b",
    "anthropic key": r"\bsk-ant-[A-Za-z0-9_-]{20,}",
    "openai-style key": r"\bsk-[A-Za-z0-9]{32,}\b",
    "slack token": r"\bxox[abprs]-[A-Za-z0-9-]{10,}",
    "google api key": r"\bAIza[0-9A-Za-z_-]{35}\b",
    "private key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "password assignment": r"(?i)\b(password|passwd|secret|api_key|apikey|token)\s*[:=]\s*['\"][^'\"\s]{6,}['\"]",
    "home path": r"/Users/[A-Za-z0-9._-]+|/home/[A-Za-z0-9._-]+|C:\\\\Users\\\\",
    "unfinished template": r"\bREPLACE\b",
}
EMAIL = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
PHONE = r"(?<![\w.])(\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?![\w.])"
SKIP_DIRS = {".git", "__pycache__", "data", "out", "node_modules"}
TEXT_LIMIT = 5_000_000


def _compile(patterns):
    out = {}
    for name, p in patterns.items():
        try:
            out[name] = re.compile(p)
        except re.error as e:
            raise SystemExit(f"scan: pattern {name!r} does not compile ({e}); refusing to report clean")
    return out


def scan(root, deny=(), strict_contacts=False, allow_emails=None):
    """Return {"fail": [...], "warn": [...]} of (file, line_no, kind, excerpt)."""
    root = Path(root)
    allow_emails = [a.lower() for a in (allow_emails if allow_emails is not None
                                        else config().get("email_allowlist", []))]
    rx = _compile(SECRETS)
    deny_rx = _compile({f"deny:{t}": r"(?i)(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])"
                        for t in deny if t and t.strip()})
    email_rx, phone_rx = re.compile(EMAIL), re.compile(PHONE)
    fail, warn = [], []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        rel = str(path.relative_to(root))
        if path.stat().st_size > TEXT_LIMIT:
            warn.append((rel, 0, "large file not scanned", f"{path.stat().st_size:,} bytes"))
            continue
        data = path.read_bytes()
        if b"\0" in data[:8192]:
            continue  # binary
        text = data.decode("utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            for name, r in {**rx, **deny_rx}.items():
                m = r.search(line)
                if m:
                    fail.append((rel, i, name, line.strip()[:160]))
            for m in email_rx.finditer(line):
                addr = m.group(0).lower()
                if any(addr.endswith(a) or addr == a for a in allow_emails):
                    continue
                (fail if strict_contacts else warn).append((rel, i, "email address", addr))
            if phone_rx.search(line):
                (fail if strict_contacts else warn).append((rel, i, "phone number", line.strip()[:160]))
    return {"fail": fail, "warn": warn}


def report(result):
    for kind in ("fail", "warn"):
        for f, i, name, ex in result[kind]:
            print(f"{kind.upper():4} {f}:{i}  {name}: {ex}")
    print(f"scan: {len(result['fail'])} failures, {len(result['warn'])} warnings")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("--deny", nargs="*", default=[])
    ap.add_argument("--strict-contacts", action="store_true")
    args = ap.parse_args()
    result = scan(args.dir, args.deny, args.strict_contacts)
    report(result)
    raise SystemExit(1 if result["fail"] else 0)


if __name__ == "__main__":
    main()
