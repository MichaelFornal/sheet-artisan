# Retro (5 min) → `catalog/*`, playbook fixes

**Goal:** the next run starts smarter. The catalog is the system's memory across runs.

1. **`catalog/sources.md`:** add every source probed in B3, including the dead ones. Record route,
   robots, terms, caps, rate behaviour, quirks, and which run used it.
2. **`catalog/ideas.md`:** add the unpicked B2 cards worth keeping, under the niche.
3. **`catalog/learnings.md`:** add traps hit, time actually spent per stage vs the budget, and
   anything a guide got wrong.
4. **`catalog/outcomes.md`:** add a row (date, company, dataset, tier, route, sent). Update it
   when a reply arrives. This is how we learn whether any of this works.
5. **Fix the playbook now** if a guide was wrong or missing a step. Commit the change in this repo.

Then run `./sa stage <slug> done`.
