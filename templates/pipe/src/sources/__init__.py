"""One module per source listed in spec.json `sources`, named after it.

A source module provides:
    NAME = "registry"
    def fetch(f, mode, sample_n): yields row dicts (spec columns + source_url + fetched_at)
    def refetch(f, row): live re-read of one row for the QA spot-check -> dict, or None if gone
"""
import importlib

from src import config


def enabled():
    mods = []
    for s in config.SPEC.get("sources", []):
        if s.get("withheld"):
            config.log(f"source {s['name']!r} is withheld from this public version; skipping it")
            continue
        mods.append(importlib.import_module(f"src.sources.{s['name']}"))
    return mods


def by_name(name):
    return importlib.import_module(f"src.sources.{name}")
