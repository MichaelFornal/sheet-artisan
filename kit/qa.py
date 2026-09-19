"""Quality gate for a finished dataset: structural checks + a live spot-check.

    result = run_checks(rows, spec, expected_rows=spec.get("expected_rows"))
    result["spot_check"] = spot_check(rows, refetch=my_refetch, fields=["name", "price"])
    open("qa.md", "w").write(to_markdown(result))

Statuses: pass / warn / fail. Any fail means the dataset is not ready for insights (B4).
"""
from __future__ import annotations

import random
import re
from collections import Counter


def _empty(v):
    return v is None or (isinstance(v, str) and not v.strip())


def _is_number(v, integer=False):
    if isinstance(v, bool):
        return False
    if isinstance(v, int) or (isinstance(v, float) and not integer):
        return True
    if isinstance(v, float) and integer:
        return v.is_integer()
    if isinstance(v, str):
        pattern = r"-?\d+" if integer else r"-?\d+(\.\d+)?([eE]-?\d+)?"
        return re.fullmatch(pattern, v.replace(",", "").strip()) is not None
    return False


def _num(v):
    return float(str(v).replace(",", "")) if not isinstance(v, (int, float)) else v


def run_checks(rows, spec, expected_rows=None, null_warn=0.5):
    cols = spec.get("columns", [])
    names = [c["name"] for c in cols]
    n = len(rows)
    checks = []

    def add(name, status, detail):
        checks.append({"name": name, "status": status, "detail": detail})

    if n == 0:
        add("row count", "fail", "no rows")
    elif expected_rows and n < 0.5 * expected_rows:
        add("row count", "warn", f"{n:,} rows, under half of the {expected_rows:,} expected")
    else:
        add("row count", "pass", f"{n:,} rows" + (f" (expected ~{expected_rows:,})" if expected_rows else ""))

    no_prov = sum(1 for r in rows if _empty(r.get("source_url")) or _empty(r.get("fetched_at")))
    add("provenance", "fail" if no_prov else "pass",
        f"{no_prov:,} rows missing source_url or fetched_at" if no_prov else "every row has source_url + fetched_at")

    key = spec.get("key") or []
    if key:
        counts = Counter(tuple(r.get(k) for k in key) for r in rows)
        dupes = {k: c for k, c in counts.items() if c > 1}
        extra = sum(c - 1 for c in dupes.values())
        examples = ", ".join(str(k if len(k) > 1 else k[0]) for k in list(dupes)[:3])
        add("unique key", "fail" if dupes else "pass",
            f"{extra:,} duplicate rows on {key} (e.g. {examples})" if dupes else f"unique on {key}")

    required = [c["name"] for c in cols if c.get("required")]
    req_bad = {c: sum(1 for r in rows if _empty(r.get(c))) for c in required}
    req_bad = {c: k for c, k in req_bad.items() if k}
    add("required columns", "fail" if req_bad else "pass",
        "; ".join(f"{c}: {k:,} empty" for c, k in req_bad.items()) or "all required columns filled")

    null_rates = {c: (sum(1 for r in rows if _empty(r.get(c))) / n if n else 0.0) for c in names}
    high = {c: v for c, v in null_rates.items() if v > null_warn and c not in required}
    add("null rates", "warn" if high else "pass",
        "; ".join(f"{c}: {v:.0%} empty" for c, v in high.items()) or f"no column over {null_warn:.0%} empty")

    type_bad, url_bad, range_bad, enum_bad = Counter(), Counter(), Counter(), Counter()
    for c in cols:
        name, t = c["name"], c.get("type", "text")
        for r in rows:
            v = r.get(name)
            if _empty(v):
                continue
            if t in ("number", "integer") and not _is_number(v, integer=(t == "integer")):
                type_bad[name] += 1
                continue
            if t == "url" and not re.match(r"https?://", str(v)):
                url_bad[name] += 1
            if t in ("number", "integer") and ("min" in c or "max" in c):
                x = _num(v)
                if ("min" in c and x < c["min"]) or ("max" in c and x > c["max"]):
                    range_bad[name] += 1
            if "enum" in c and v not in c["enum"]:
                enum_bad[name] += 1
    bad_types = type_bad + url_bad
    add("types", "warn" if bad_types else "pass",
        "; ".join(f"{c}: {k:,} bad values" for c, k in bad_types.items()) or "numbers parse, urls are http(s)")
    add("ranges", "warn" if range_bad else "pass",
        "; ".join(f"{c}: {k:,} out of range" for c, k in range_bad.items()) or "all within declared ranges")
    add("allowed values", "warn" if enum_bad else "pass",
        "; ".join(f"{c}: {k:,} unexpected" for c, k in enum_bad.items()) or "all within declared sets")

    seen = set()
    for r in rows:
        seen.update(k for k in r if not k.startswith("_"))
    unknown = sorted(seen - set(names))
    add("unknown columns", "warn" if unknown else "pass",
        ("not in spec (dropped from the sheet): " + ", ".join(unknown)) if unknown else "rows match the spec")

    return {"checks": checks, "passed": not any(c["status"] == "fail" for c in checks),
            "row_count": n, "null_rates": null_rates}


def _norm(v):
    return re.sub(r"\s+", " ", str(v)).strip().lower() if v is not None else ""


def spot_check(rows, refetch, fields, n=20, seed=0):
    """Re-fetch `n` random rows live via `refetch(row) -> dict | None` and compare `fields`."""
    sample = random.Random(seed).sample(rows, min(n, len(rows)))
    counts = Counter()
    details = []
    for r in sample:
        try:
            fresh = refetch(r)
        except Exception as e:
            counts["error"] += 1
            details.append({"url": r.get("source_url"), "result": "error", "detail": repr(e)[:200]})
            continue
        if fresh is None:
            counts["gone"] += 1
            details.append({"url": r.get("source_url"), "result": "gone", "detail": "no longer at source"})
            continue
        diffs = [f"{f}: {r.get(f)!r} -> {fresh.get(f)!r}" for f in fields if _norm(r.get(f)) != _norm(fresh.get(f))]
        counts["changed" if diffs else "match"] += 1
        details.append({"url": r.get("source_url"), "result": "changed" if diffs else "match",
                        "detail": "; ".join(diffs)})
    k = len(sample)
    match_rate = counts["match"] / k if k else 0.0
    status = "pass" if match_rate >= 0.9 else "warn" if match_rate >= 0.6 else "fail"
    return {"sampled": k, "match": counts["match"], "changed": counts["changed"], "gone": counts["gone"],
            "error": counts["error"], "match_rate": match_rate, "status": status, "details": details}


def to_markdown(result, limits=()):
    lines = ["# QA", "", f"Rows: {result['row_count']:,} · Passed: {'yes' if result['passed'] else 'NO'}", "",
             "| Check | Status | Detail |", "|---|---|---|"]
    for c in result["checks"]:
        lines.append(f"| {c['name']} | {c['status']} | {c['detail']} |")
    s = result.get("spot_check")
    if s:
        lines += ["", "## Live spot-check",
                  f"{s['sampled']} random rows re-fetched: {s['match']} match, {s['changed']} changed, "
                  f"{s['gone']} gone, {s['error']} errors → **{s['status']}**", ""]
        for d in s["details"]:
            if d["result"] != "match":
                lines.append(f"- {d['result']}: {d['url']} {d['detail']}")
    if limits:
        lines += ["", "## Known limits", *[f"- {x}" for x in limits]]
    return "\n".join(lines) + "\n"


def sheet_rows(result, limits=()):
    """(check, status, detail) rows for the workbook's QA & Limits tab."""
    out = [(c["name"], c["status"], c["detail"]) for c in result["checks"]]
    s = result.get("spot_check")
    if s:
        out.append(("live spot-check", s["status"],
                    f"{s['sampled']} random rows re-fetched: {s['match']} match, {s['changed']} changed, "
                    f"{s['gone']} gone, {s['error']} errors"))
    out += [("known limit", "note", x) for x in limits]
    return out
