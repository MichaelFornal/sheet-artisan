# Sample check (live · 5 min)

**Goal:** Mike sees real rows before hours of crawling. A spec change is cheap now and expensive
after a 6-hour crawl.

## Present
- 10–15 sample rows as a markdown table, with the columns that matter most for the aimed decisions.
- Columns that came back mostly empty, and why.
- The full-crawl estimate: requests, time at the current rate, expected rows.
- Open the sample workbook for him: `open runs/<slug>/out/*_SAMPLE_*.xlsx`.

## Ask
1. Is this what we meant? Options: yes, crawl · change columns · change scope · rethink.
2. When should the full crawl start? Options: now, in the background · now, and wait here · later.

## Record
- `./sa decide <slug> sample "…"`

If the spec changed, update `spec.json` and `03_spec.md`, then rerun `make sample`. Once it's a yes,
`./sa stage <slug> crawl "<estimate>"`.
