# QA (autonomous · 10 min) → `out/qa.md`

**Goal:** know the dataset is true before anyone draws conclusions from it. **Any `fail` blocks
B4.**

```
make sheet     # structural checks + the full workbook
make spot      # re-fetches 20 random rows live and compares spot_check_fields
```
Read `out/qa.md`.

| Check | If it fails or warns |
|---|---|
| row count | Far under `expected_rows`: a partition hit a cap, a source broke, or the estimate was wrong. Find out which. |
| provenance | A source isn't setting `source_url`/`fetched_at`. Fix the source. |
| unique key | The key isn't unique. Fix the dedupe key or the join, then `make clean && make full` (the cache makes this fast). |
| required columns | A parser misses a field. Fix it using saved responses. |
| null rates / types / ranges | Explain real gaps in `spec.limits`; fix parser bugs. |
| spot-check < 90% match | Fields that legitimately drift (prices, counts) → note them in limits. Parsing errors → fix. |

Every known gap goes into `spec.json` `limits`, which feeds the workbook's QA & Limits tab. Saying
what the data can't do is part of what makes it credible.

Then run `./sa stage <slug> b4`.
