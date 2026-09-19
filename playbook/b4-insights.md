# B4 · Insights & business uses (live · 20 min · 0 searches) → `04_insights.md`

**Goal:** turn rows into a headline and 3–5 uses the company could act on, every one backed by a
computed fact and a ready-made tab.

## Prepare: profile the full data
Load `pipe/data/rows.full.jsonl` (for example a quick script in `pipe/`) and look for:
- **Counts and distributions** along each aimed decision's dimension.
- **Concentration:** the top 10% share, the top 10 names.
- **Gaps:** segments or places with zero or little, where you'd expect more.
- **Outliers and surprising absences.**
- **Cross-tabs** against the aimed decisions (e.g. prospects × trigger signal × region).
- **Change**, when there's a time dimension.

Write **8–10 candidate findings** in `04_insights.md`. Each gets:
- the finding
- its number(s)
- why *they* would care
- the `facts_def.py` function that computes it

Add the functions now; `make sheet` writes them to `out/facts.full.json`.

Write **6–8 candidate uses**. Each gets:
- the use
- who on their team
- the exact filter and sort (this becomes its tab)
- what they'd do Monday morning
- 3 example rows

## Overclaiming rules
- No causal claims from counts.
- No revenue or market-size estimates unless computed from the sheet's own data, with the
  assumptions written on the tab.
- If coverage is partial, say "at least N".
- "Only", "first", "nobody" and "every" need proof, or they go.

## Present
The findings table, then the uses table.

## Ask
1. Which finding is the headline, the one that opens the email? (single select)
2. Which 3–5 uses? (multiSelect)
3. Does anything read as an overclaim, or as something they already know?

## Record
- `./sa decide <slug> headline "…"`
- `./sa decide <slug> uses "…"`

Then implement:
- `uses.py`: one tab per chosen use.
- `package/start_here.md`: the headline with `{{fact:…}}` numbers, and one line per use linking to
  its tab, `[text](#Tab name)`.

`make sheet`, then `./sa stage <slug> package`.
