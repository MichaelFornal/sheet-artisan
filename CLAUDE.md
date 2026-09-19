# Sheet Artisan

One run = one company. We research its niche with Mike, brainstorm a dataset nobody has handed
them, build the pipe that collects it, and deliver an Excel workbook with concrete business uses as
part of an application package. The pipe goes on GitHub, or deliberately doesn't. **Mike is live in
every brainstorm.** The design and the reasons behind it are in `docs/design.md`.

## Start or resume
- **New run:** `./sa new "Company" [--posting URL] [--domain company.com]` creates `runs/<slug>/`.
- **Resume:** run `./sa status` and then `./sa status <slug>`, which names the stage and its guide.
  Read `runs/<slug>/run.md` (resume notes, decisions, log) and the stage docs before doing anything.
- **Advance** at the *start* of each stage: `./sa stage <slug> <stage> "note"`.
- **Record every brainstorm decision:** `./sa decide <slug> <key> "value"`.

## The run
| Stage | Guide | Mike | Writes | Time |
|---|---|---|---|---|
| b1 | `playbook/b1-company.md` | **live** | `01_brief.md` (decision map) | 20 min |
| b2 | `playbook/b2-ideation.md` | **live** | `02_ideas.md` (12–15 scored cards) | 25 min |
| b3 | `playbook/b3-sources.md` | **live** | `03_spec.md`, `pipe/spec.json` (frozen) | 35 min |
| build | `playbook/build.md` | — | `pipe/src/…`, sample workbook | ~60 min |
| sample-check | `playbook/sample-check.md` | **live** | go/no-go on the full crawl | 5 min |
| crawl | `playbook/crawl.md` | — | `pipe/data/rows.full.jsonl` | unattended |
| qa | `playbook/qa.md` | — | `out/qa.md`, spot-check | 10 min |
| b4 | `playbook/b4-insights.md` | **live** | `04_insights.md`, `facts_def.py`, `uses.py` | 20 min |
| package | `playbook/package.md` | — | `package/*`, workbook, email, README | 20 min |
| b5 | `playbook/b5-ship.md` | **live** | go / no-go, publish | 15 min |
| retro | `playbook/retro.md` | — | `catalog/*`, playbook fixes | 5 min |

Sitting 1 is b1 through sample-check. Sitting 2 is qa through retro. The crawl runs between them.

## How every brainstorm runs
1. **Prepare first.** Do the research or probing before saying anything, and write the stage doc.
2. **Present the compact artifact**: the summary table the guide names, not the whole doc.
3. **Ask 2–4 pointed questions** with AskUserQuestion. Use multiple choice with your recommended
   option first, and let Mike add his own through "Other".
4. **Record** with `./sa decide`, fix the stage doc with his corrections, then advance.

Never decide for Mike at a brainstorm. If he says "you pick", record that he delegated.

## Search budget
WebSearch is capped at ~200 per **session**, shared by every subagent. The buckets are
b1 ≤30 · b2 ≤30 · b3 ≤60 · reserve 40 (build and recipient lookup). Count each search:
`./sa search <slug> <bucket> [N]`. When a bucket is spent, WebFetch known URLs instead. Any
subagent you launch (up to 3 in parallel for b1 research or b3 probing) must be told its search cap.

## The floor (never negotiable)
- **Access:** public data only. Never get around logins, paywalls, CAPTCHAs or blocks. robots.txt
  is honoured by `kit/fetch.py`, which has no off switch; don't write around it. A source that
  blocks us is dropped, not evaded.
- **Provenance:** every row carries `source_url` and `fetched_at`. Nothing is invented. AI-derived
  columns are marked `"ai": true` in `spec.json` and their answers are cached.
- **Numbers:** every number in Start Here, the email and the README is a `{{fact:key}}` computed
  in `facts_def.py`. `./sa claims` / `./sa check` fail on any hand-typed number.
- **Personal data:** only what people published professionally about themselves. `sensitivity` in
  `spec.json` decides which sharing tiers are allowed (none → any; personal/outreach/sensitive →
  private or none).
- **Recipient email:** use a self-published address first. Otherwise derive the company's pattern
  from ≥1 real address at that domain found on the public web, record the evidence URLs, and label
  the address "pattern-derived". No SMTP probing, no paid finders.
- **Outward actions:** `./sa publish … --go`, repo invites and sending the email happen only after
  Mike's explicit go in b5. Mike sends the email himself.
- **$0:** free sources, plus `claude -p` for AI steps.

## Commands
```
./sa new | status | stage | search | decide     run bookkeeping
./sa check <slug> [--tier T]                    the b5 gate (facts, QA, drafts, workbook, links)
./sa publish <slug> --tier public|private|none  stage + scan (dry run); add --go only on Mike's go
./sa scan <dir> · ./sa claims FILE…             the two gates on their own
./sa test                                       this system's tests
```
Inside `runs/<slug>/pipe/`: `make sample | full | sheet | spot | readme | offline | clean`.

## Layout
```
playbook/     one guide per stage: read the guide before starting its stage
templates/    run/ (stage docs), package/ (Start Here, email, recipient), pipe/ (the pipe skeleton)
kit/          fetch · llm · facts · qa · workbook; copied into every pipe so published repos stand alone
tools/        new_run · stage · check_run · publish · scan · claims_check (behind ./sa)
catalog/      sources.md · ideas.md · learnings.md · outcomes.md; grows every run, read it in b2/b3
runs/<slug>/  gitignored: run.json/run.md, 01–04 docs, package/, pipe/ (its own git repo), out/
```

## Conventions
- System Python 3.9 with the standard library plus `openpyxl` (no pyyaml, no pytest). Tests use
  `unittest`: `./sa test`.
- Fix a kit bug **here**, in `kit/`, with a test; then copy the file into the run's `pipe/kit/`.
  Never patch a run's copy alone.
- `runs/` never leaves this machine except through `./sa publish`. This repo has no remote.
- Commit this repo's changes with a short message. Runs are not committed here.
