# B1 · Company read-back (live · 20 min · ≤30 searches) → `01_brief.md`

**Goal:** understand the company well enough to aim a dataset at decisions its people actually
make. The dataset is only valuable if it changes one of those decisions.

`./sa stage <slug> b1` first.

## Prepare (before talking to Mike)
Use WebFetch on URLs you already know before spending searches, and count every search
(`./sa search <slug> b1`). Two parallel research agents are fine; give each a cap of 10 searches.

1. **Their site:** home, product/pricing, customers and case studies, about, careers, the last few
   blog/changelog titles, docs/API.
2. **The posting** (if any): the role, the team, the skills named, what "success" looks like.
3. **Stage and money:** funding announcements, investors, rough headcount (careers page count,
   team page).
4. **Competitors (3–5):** their own comparison pages, "X alternatives", review-site categories.
5. **What's changing:** launches, new markets, pricing changes and hires in the last ~6 months.
6. **Public-data footprint:** do they publish an API, open data, a status page, public GitHub, a
   changelog? What data does their product already ingest? This tells you what they value.

Keep every URL you used; they go in the brief's Sources list.

## Write `01_brief.md` (template in the run folder)
- **The company in one paragraph.**
- **Who buys, why, and how they pay** (ICP, pricing model, sales motion).
- **Stage / size / geography.**
- **What's changing.**
- **The role** (if posting): the skills this dataset should visibly prove.
- **Decision map:** 6–8 rows, each with *decision · who makes it · how often · information
  they'd want · what they likely use today · gap?* Think across:
  - sales (who to call next)
  - marketing (which segment or message)
  - product (what to build next)
  - expansion (where)
  - pricing, partnerships, hiring, risk/compliance
- **Recipient hypothesis:** who reads this (founder, head of X, hiring manager), what they care
  about, and what would make them forward it.

## Present
The decision map table, a three-line company summary, and the recipient hypothesis. Nothing else.

## Ask (AskUserQuestion)
1. Which 2–3 decisions should the dataset serve? Use multiSelect over the decision map, with your
   recommendation first.
2. Who is the recipient? Options come from the hypothesis.
3. Is anything wrong or missing? Is there an angle you already have in mind? (Free text via
   "Other".)

## Record
- `./sa decide <slug> decisions "…"`
- `./sa decide <slug> recipient "…"`
- `./sa decide <slug> angle "…"` (if he gave one)
- `./sa decide <slug> domain company.com` if the run was started without `--domain`. This also
  adds the domain to the terms the public-tier scan refuses.

Apply his corrections to `01_brief.md`, then `./sa stage <slug> b2`.
