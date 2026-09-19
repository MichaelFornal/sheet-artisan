"""make sample / make full: every source -> dedupe -> derive -> data/rows.<mode>.jsonl

Resumable by construction: every HTTP answer is cached, so re-running after a crash replays the
finished part from disk in seconds and carries on where the network work stopped.
"""
import json
import os
import time

from src import config, derive, sources


def dedupe(rows, key):
    if not key:
        return rows, 0
    seen, out, dupes = set(), [], 0
    for r in rows:
        k = tuple(r.get(c) for c in key)
        if all(v is None for v in k):
            out.append(r)
            continue
        if k in seen:
            dupes += 1
            continue
        seen.add(k)
        out.append(r)
    return out, dupes


def _write_json(path, doc):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, default=str))
    os.replace(tmp, path)


def main():
    config.DATA.mkdir(parents=True, exist_ok=True)
    started = time.time()
    f = config.fetcher()
    rows, per_source = [], {}
    progress = config.DATA / f"progress.{config.MODE}.json"
    for mod in sources.enabled():
        n = 0
        for row in mod.fetch(f, config.MODE, config.SAMPLE_N):
            row.setdefault("_source", mod.NAME)
            rows.append(row)
            n += 1
            if n % 500 == 0:
                config.log(f"{mod.NAME}: {n:,} rows · {f.stats}")
                _write_json(progress, {"mode": config.MODE, "source": mod.NAME, "rows": n,
                                       "per_source": per_source, "stats": f.stats, "updated": time.time()})
        per_source[mod.NAME] = n
        config.log(f"{mod.NAME}: done, {n:,} rows")
    rows, dupes = dedupe(rows, config.SPEC.get("key") or [])
    rows = derive.apply(rows)

    out = config.rows_path()
    tmp = out.with_suffix(".tmp")
    with tmp.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=str) + "\n")
    os.replace(tmp, out)
    meta = {"mode": config.MODE, "rows": len(rows), "per_source": per_source, "duplicates_dropped": dupes,
            "fetch_stats": f.stats, "seconds": round(time.time() - started, 1)}
    _write_json(config.DATA / f"build.{config.MODE}.json", meta)
    _write_json(progress, {**meta, "done": True, "updated": time.time()})
    config.log(f"wrote {len(rows):,} rows to {out.relative_to(config.ROOT)} ({dupes:,} duplicates dropped) · {f.stats}")


if __name__ == "__main__":
    main()
