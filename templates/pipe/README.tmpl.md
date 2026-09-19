# {{var:title}}

{{var:grain}}. The last full run collected {{fact:row_count}} rows from {{fact:source_count}} public sources.

## Why this exists

REPLACE: what decision this data serves, and why it did not exist as one table before.

## What's hard about it

REPLACE: the real engineering (pagination caps, entity matching, rate limits, messy sources).

## Run it

```bash
pip install -r requirements.txt
make sample     # a small run, straight to a workbook in out/
make full       # the whole crawl; safe to stop and re-run, it resumes from its cache
make sheet      # QA checks + the workbook from the full crawl
make spot       # re-fetch random rows live and compare them to the dataset
```

The fetcher honours robots.txt, identifies itself, waits between requests and backs off when asked.

## What you get

A workbook with **Start Here**, **Data**, **Summary**, **Dictionary**, **Sources & Method** and
**QA & Limits** tabs. `sample/sample_rows.csv` shows the first rows of a real run.

## Sources

Every source, its terms and how it is read are listed in `spec.json` and in the workbook's
Sources & Method tab.

## Layout

```
spec.json          the dataset contract: grain, columns, key, sources
src/sources/       one module per source
src/build.py       sources -> dedupe -> derive -> data/rows.<mode>.jsonl
src/facts_def.py   every number quoted in prose, as code
src/sheet.py       the workbook
kit/               fetch (cache, robots, backoff), qa, facts, workbook
```
