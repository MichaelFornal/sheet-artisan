# B3 · Source spike & spec freeze (live · 35 min · ≤60 searches) → `03_spec.md`, `pipe/spec.json`

**Goal:** prove each shortlisted idea against real sources with **one real request each**, kill
what fails, then freeze the spec of the one Mike picks. Nothing in B2 counts as feasible until a
request has come back.

## Probe every candidate source
Look for the route in this order: official API → bulk download → sitemap → HTML listing → PDF.
Take the first that works. For each source, record:

1. **Endpoint / URL and method.** Check `catalog/sources.md` first; it may already be mapped.
2. **robots.txt:** fetch it and check the exact paths you need. Note any `Crawl-delay`.
3. **Terms / licence:** find the terms page and the data licence (public record, CC-BY,
   API terms), plus any clause about automated access.
4. **One real request** (`curl -A "sheet-artisan-pipe/0.1"` or WebFetch). Paste a trimmed real
   record into `03_spec.md`: these are the fields that actually exist, not the ones we hope for.
5. **Pagination and caps:**
   - page size and rate-limit headers;
   - result caps. A 1,000-result cap means partitioning by date, geography or category; write the
     partition plan down.
6. **Coverage estimate:** the API's total count, sitemap size, or listing count.
7. **Full-crawl time:** requests ÷ rate (default 1 req/s, or the Crawl-delay if slower).
8. **Publish flag:**
   - `public` for an ordinary documented route;
   - `private` for an undocumented endpoint or a method Mike doesn't want broadcast. The public
     repo will withhold that source's code and URL.
9. **AI step needed?** (the B2 test)

**Kill a candidate when:**
- it needs a login, paywall or CAPTCHA;
- robots.txt disallows the paths it needs;
- the terms prohibit it and there is no official route;
- coverage is too thin to change a decision;
- the crawl is over 24 h and can't be narrowed.

## Present
A feasibility table: `candidate · sources · route · robots · terms · rows · crawl time · publish ·
verdict`. Below it, the draft spec for the leading candidate.

## Ask
1. Which is the final dataset? Options are only candidates whose verdict passed.
2. Confirm scope and size: filters (geography, size, date window) and the target row count.
3. Provisional sharing tier. Offer only the tiers the sensitivity allows.

## Freeze the spec
Write `pipe/spec.json`, the contract the whole pipe and every gate reads:
- `title` and `niche_slug`: name the **niche**, never the company. The slug becomes the repo name.
- `grain`, `key` (the dedupe key), `sensitivity`, `tier`, `expected_rows`, `rate`,
  `spot_check_fields`, `limits`.
- `columns`: `name`, `type` (text/integer/number/url/datetime/bool), `definition` (required),
  `source`, `derived`, `ai`, `required`, `min`/`max`, `enum`. Always keep `source_url` and
  `fetched_at`.
- `sources`: one entry per source module, with `name` (= `src/sources/<name>.py`), `url`,
  `method`, `robots`, `license`, `publish`, `notes`.

`03_spec.md` keeps the reasoning:
- the feasibility table
- pasted sample records
- how sources join (exact id, domain, or normalized name + city)
- the partition plan
- the AI prompt and its output schema
- sample N and the full-crawl estimate

Record:
- `./sa decide <slug> dataset "…"`
- `./sa decide <slug> tier "…"`

Commit the spec in the pipe repo, then `./sa stage <slug> build`.
