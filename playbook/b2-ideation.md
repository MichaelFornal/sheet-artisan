# B2 · Dataset ideation (live · 25 min · ≤30 searches) → `02_ideas.md`

**Goal:** 12–15 concrete candidate datasets, scored the same way every run, so Mike picks 2–3
worth probing. Read `catalog/ideas.md` and `catalog/sources.md` first: earlier runs may already
have mapped this niche.

## Generate: walk every lens against the aimed decisions
The fixed lens list is what stops every run from converging on "a competitor list". Aim for at
least one card per lens, then keep the best 12–15.

1. **Prospects / customers:** who they should sell to next, with a *trigger signal* (just
   raised, just hired X, just opened a location, just got a permit, just changed vendor).
2. **Competitors & market map:** every player, with positioning, pricing, customers, momentum.
3. **Partners / channel / supply:** integrators, resellers, suppliers, complementary tools.
4. **Public records & regulation:** permits, licences, inspections, filings, grants, government
   contracts, recalls, patents, court dockets.
5. **Demand & sentiment:** reviews, forums, job postings as a proxy for budgets, app stores,
   community questions.
6. **Prices & catalogs:** pricing pages, menus, SKUs, rate cards, over time.
7. **Geography & coverage gaps:** locations, service areas, where demand exists and supply doesn't.
8. **Change over time:** a snapshot now, plus a repeatable diff ("new this month").
9. **Their own public footprint:** how they appear in public data (reviews, mentions, listings,
   integrations directories).
10. **The wildcard join:** two public sources nobody has joined, where the join itself is the value.

## Card (one per idea, in `02_ideas.md`)
- **title**
- **grain:** one row = …
- **columns:** 6–8
- **decision served:** which aimed decision it serves, and how
- **candidate sources**
- **existence check:** can they already buy or download this? Where, and at what price?
- **est. rows · est. crawl time · feasibility risk**
- **10-second wow:** what they see on the first screen
- **skill shown:** what it proves about Mike, matched to the posting when there is one
- **AI step?** yes or no, and why (the test is below)
- **sensitivity:** none / personal / outreach / sensitive, which sets the allowed tiers

## Existence check (top ~6 cards, ≤2 searches each)
Search "<topic> dataset", "<topic> list download", and "<topic> database" on data vendors
(Crunchbase, ZoomInfo, Apollo, BuiltWith, PitchBook, Kaggle, data.world, government open-data
portals). A free, current download means low uniqueness. A paid or stale one still leaves room if
ours is fresher, joined, or niche-specific. Say which in the card.

## The AI-step test
Use an LLM column only when **both** hold:
- (a) a column an aimed decision needs cannot be pulled from the raw text with rules at >90%
  accuracy (free-text classification, extracting fields from prose or PDFs, matching messy names);
- (b) the volume fits. `claude -p` handles about 20 rows per call, at roughly 5–10 s per call.

Otherwise, don't. Mark AI columns `"ai": true`.

## Legitimacy gate (pass or drop, not a score)
- Reachable without login, paywall or CAPTCHA.
- robots.txt allows the paths needed (verified in B3).
- The terms don't prohibit automated collection, or an official API or bulk download exists. If
  the terms prohibit it and there's no official route, drop the card.
- Personal data: only professional, self-published information, and the sensitivity must say so.

## Score (1–5 each; total out of 50)
| | Weight | 5 means | 1 means |
|---|---|---|---|
| Value | ×3 | directly changes an aimed decision, with money attached | merely interesting |
| Uniqueness | ×2 | not buyable or downloadable; needs a join or parsing | a free current download exists |
| Feasibility | ×2 | one clean source, crawl < 2 h | several fragile sources, crawl > 1 day |
| Wow | ×2 | "how did you get this?" | obvious |
| Showcase | ×1 | exercises exactly the skills the role wants | a trivial pipe |

## Present
A ranked table with columns: `# · idea · grain · decision · V U F W S = total · sensitivity ·
10-second wow`. Below it, one line for each remaining card.

## Ask
1. Which 2–3 go to the source spike? Use multiSelect over the top 4, recommendation first.
2. Kill, merge or modify any? Add your own? ("Other".)

## Record
- `./sa decide <slug> shortlist "…"`

Unpicked cards stay in `02_ideas.md`; retro copies the good ones into `catalog/ideas.md`. Then
`./sa stage <slug> b3`.
