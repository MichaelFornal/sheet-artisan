# Build (~60 min, autonomous) → `pipe/src/…`, a sample workbook

**Goal:** a pipe that turns `spec.json` into rows, and a workbook built from a *sample* before the
long crawl starts. Work inside `runs/<slug>/pipe/` and commit there as each source starts working.

## Sources: one module per `spec.json` source
Replace `src/sources/example.py` (delete it and its spec entry). Every module follows the same
contract:
```python
NAME = "registry"                      # == the spec.json source name == the file name
def fetch(f, mode, sample_n):          # yield one dict per row
    ...                                # stop after sample_n rows when mode == "sample"
def refetch(f, row):                   # live re-read for the QA spot-check
    ...                                # f.get(url, fresh=True); return None if gone
```
- **Always go through the kit Fetcher.** That is what gives caching, resume, robots, throttling and
  backoff. Never call `urllib`/`requests` directly.
- **Every row carries `source_url`**, the most specific URL a human can open to check it, and
  **`fetched_at`** (`r.fetched_at`).
- **Partitions:** when a source caps results, loop over the partitions from `03_spec.md`, and log
  any partition that still hits the cap.
- **Check the response, not just the status:** a 200 with an error page or an empty list is a
  failure. Assert on shape early.

## Normalize, join, derive
- **Normalize values:** strip whitespace; ISO dates; numbers as numbers; one unit per column;
  canonical URLs (no tracking params).
- **Joins:** match on the strongest shared key first (id → domain → normalized name + city).
  Normalize names by lowercasing, dropping punctuation and legal suffixes (inc, llc, ltd, corp).
  When a match method is fuzzy, add a column saying which method matched.
- **Dedupe:** handled by `spec.key` in `build.py`. Choose the key so duplicates really are the
  same entity.
- **Derived and AI columns:** go in `src/derive.py`, using the pattern in its docstring.
  `llm.map_batched` caches per item, so reruns are free.

## Facts, uses, summary: minimal now, finished in B4
`facts_def.py` starts with `row_count` and `source_count`. `summary.py` adds one table per aimed
decision (a count by the dimension that decision cares about).

## Run the sample
```
make sample          # SAMPLE_N=25 by default; SAMPLE_N=100 make sample for more
```
Read the log, open `out/qa.md`, and open the sample workbook (`open ../out/*_SAMPLE_*.xlsx`). Fix
anything broken before the sample check.

Draft `README.tmpl.md` now while the details are fresh: *why this exists* and *what's hard about
it*. Mike edits it in B5.

## Parsers worth a test
When a parser is fiddly (HTML tables, PDF text, dates in prose), save 2–3 real responses from
`data/cache/` as fixtures and add a small `tests/` file in the pipe. The published repo then shows
the parsing works.

Then run `./sa stage <slug> sample-check`.
