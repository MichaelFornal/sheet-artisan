"""EXAMPLE source: delete it once a real source exists (and drop it from spec.json).

It shows the pattern every source follows: page through a JSON API with the kit Fetcher (cached,
polite, resumable), emit one row per record with its provenance, stop early in sample mode.
"""
import os

from kit.fetch import FetchError

NAME = "example"
BASE = os.environ.get("SA_EXAMPLE_BASE")  # only set by Sheet Artisan's own end-to-end test


def _row(item, fetched_at):
    return {
        "name": item["name"],
        "category": item.get("category"),
        "employees": item.get("employees"),
        "source_url": f"{BASE}/items/{item['id']}",
        "fetched_at": fetched_at,
    }


def fetch(f, mode, sample_n):
    if not BASE:
        raise SystemExit("src/sources/example.py is a placeholder: write the real sources (playbook/build.md)")
    page, n = 1, 0
    while True:
        r = f.get(f"{BASE}/api/items", params={"page": page})
        if not r.ok:
            raise FetchError(f"{r.status} on page {page}")
        data = r.json()
        for item in data["items"]:
            yield _row(item, r.fetched_at)
            n += 1
            if mode == "sample" and n >= sample_n:
                return
        if not data.get("next"):
            return
        page += 1


def refetch(f, row):
    r = f.get(row["source_url"], fresh=True)
    if r.status in (404, 410):
        return None
    return _row(r.json(), r.fetched_at)
