"""Small computed tables for the Summary tab (a chart is drawn when `chart` is given)."""
from collections import Counter


def tables(rows):
    by_source = Counter(r.get("_source") for r in rows)
    return [{"title": "Rows by source", "header": ["source", "rows"],
             "rows": [[k, v] for k, v in by_source.most_common()],
             "chart": {"type": "bar", "title": "Rows by source"}}]
