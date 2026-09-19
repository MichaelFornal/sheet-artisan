"""Command-backed numbers. Every number a reader sees in prose is computed, never typed.

    facts = Facts()

    @facts.fact("clinic_count", "Clinics in the dataset", fmt="int")
    def clinic_count(rows):
        return len(rows)

    computed = facts.compute(rows)        # {key: {"value", "display", "desc"}}
    save(computed, "out/facts.json")
    render("We mapped {{fact:clinic_count}} clinics.", computed)

Prose templates (Start Here, email, README) may contain digits only inside {{fact:key}},
{{lit:...}} (a literal that is not a claim, e.g. {{lit:24/7}}) or {{var:name}} (company, repo URL).
`bare_numbers(template)` finds every other digit; tools/claims_check.py fails on any.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


class FactError(Exception):
    pass


def _fmt(value, fmt):
    if value is None:
        return "n/a"
    if callable(fmt):
        return fmt(value)
    if fmt == "int":
        return f"{int(round(value)):,}"
    if fmt == "pct":
        return f"{value * 100:.0f}%"
    if fmt == "pct1":
        return f"{value * 100:.1f}%"
    if fmt == "money":
        return f"${value:,.0f}"
    if fmt == "float1":
        return f"{value:,.1f}"
    if fmt == "float2":
        return f"{value:,.2f}"
    if fmt == "text":
        return str(value)
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.1f}"
    return str(value)


class Facts:
    def __init__(self):
        self._defs = {}

    def fact(self, key, desc, fmt="auto"):
        if not re.fullmatch(r"[a-z0-9_]+", key):
            raise FactError(f"fact keys are lower_snake_case: {key!r}")
        if key in self._defs:
            raise FactError(f"fact {key!r} defined twice")

        def deco(fn):
            self._defs[key] = (fn, desc, fmt)
            return fn
        return deco

    def keys(self):
        return list(self._defs)

    def compute(self, rows, **ctx):
        out = {}
        for key, (fn, desc, fmt) in self._defs.items():
            value = fn(rows, **ctx) if ctx else fn(rows)
            out[key] = {"value": value, "display": _fmt(value, fmt), "desc": desc}
        return out


def save(computed, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"_meta": {"computed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()},
           **computed}
    path.write_text(json.dumps(doc, indent=2, default=str))


def load(path):
    doc = json.loads(Path(path).read_text())
    doc.pop("_meta", None)
    return doc


_PLACEHOLDER = re.compile(r"\{\{(fact|lit|var):([^}]*)\}\}")


def render(template, facts, variables=None):
    variables = variables or {}
    missing = []

    def sub(m):
        kind, name = m.group(1), m.group(2).strip()
        if kind == "lit":
            return m.group(2)
        if kind == "fact":
            if name not in facts:
                missing.append(f"fact:{name}")
                return m.group(0)
            return str(facts[name]["display"])
        if name not in variables or variables[name] in (None, ""):
            missing.append(f"var:{name}")
            return m.group(0)
        return str(variables[name])

    out = _PLACEHOLDER.sub(sub, template)
    if missing:
        raise FactError("unresolved placeholders: " + ", ".join(sorted(set(missing))))
    return out


def placeholders(template, kind="fact"):
    return sorted({m.group(2).strip() for m in _PLACEHOLDER.finditer(template) if m.group(1) == kind})


_STRIP = [
    re.compile(r"```.*?```", re.S),                    # fenced code
    re.compile(r"`[^`\n]*`"),                          # inline code
    re.compile(r"<!--.*?-->", re.S),                   # comments
    _PLACEHOLDER,                                      # backed values
    re.compile(r"\]\([^)]*\)"),                        # markdown link targets
    re.compile(r"https?://\S+"),                       # bare URLs
    re.compile(r"\b\d{4}-\d{2}-\d{2}(T[\d:.]+Z?)?\b"),  # ISO dates
    re.compile(r"^\s*\d+[.)]\s", re.M),                # list numbering
    re.compile(r"\b[A-Za-z][A-Za-z]*\d[A-Za-z0-9]*\b"),  # B2B, Q3, S3, GPT4 (letter-led tokens)
]


def bare_numbers(template):
    """[(line_number, line_text)] for every line with a digit that no fact/lit/var backs."""
    text = template
    for rx in _STRIP:
        text = rx.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
    hits = []
    for i, (clean, orig) in enumerate(zip(text.split("\n"), template.split("\n")), 1):
        if re.search(r"\d", clean):
            hits.append((i, orig.strip()))
    return hits
