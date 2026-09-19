"""Derived columns, computed after dedupe. The AI step lives here when it earns its place.

Pattern for an AI column (mark it "derived": true, "ai": true in spec.json):

    llm = config.llm()
    if llm.available() or config.OFFLINE:
        out = llm.map_batched(rows, instruction="Classify each business into one category.",
                              item_schema={"type": "object", "required": ["category"],
                                           "properties": {"category": {"type": "string",
                                                                       "enum": ["a", "b", "other"]}}},
                              render=lambda r: {"id": r["source_url"], "name": r["name"]})
        for r in rows:
            r["category"] = (out.get(r["source_url"]) or {}).get("category")
    else:
        config.log("claude CLI not found: AI columns left blank")
"""
from src import config  # noqa: F401  (used by the AI pattern above)


def apply(rows):
    return rows
