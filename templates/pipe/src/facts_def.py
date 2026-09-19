"""Every number that appears in prose (Start Here, email, README) is defined here, as code.

Add one @facts.fact per finding chosen in B4, then reference it as {{fact:key}} in the templates.
"""
from kit.facts import Facts

facts = Facts()


@facts.fact("row_count", "Rows in the dataset", fmt="int")
def row_count(rows):
    return len(rows)


@facts.fact("source_count", "Sources that contributed rows", fmt="int")
def source_count(rows):
    return len({r.get("_source") for r in rows})
