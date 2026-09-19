# Crawl (unattended: minutes to many hours)

**Goal:** the full dataset, collected politely, surviving interruptions.

## Start it
In the pipe, as a background Bash task:
```
caffeinate -i make full > data/full.log 2>&1
```
- Keep the Mac **plugged in**. `caffeinate -i` doesn't stop low-battery sleep, and a crawl that
  "hung" for hours is usually a Mac that hibernated.
- Progress is in `data/progress.full.json` (rows so far, current source, fetch stats) and in
  `data/full.log`.
- Write a resume note in `run.md` ("full crawl started HH:MM, est. N h, log at …"), then
  `./sa stage <slug> crawl "started HH:MM"`.

## While it runs
- To watch it, use a Monitor loop that waits until the progress file says `done`. Don't poll
  every minute.
- If it dies, run `make full` again. Every finished request replays from `data/cache/` in seconds,
  so it picks up where the network stopped.
- **429 storms:** the fetcher slows itself and decays back to normal. Don't raise the rate to "catch
  up"; that makes it slower.
- **A source starts refusing us** (persistent 403, a CAPTCHA page, a robots change): stop that
  source and tell Mike. Never switch IPs, user agents or headers to get around it.
- The session can end here. The next session resumes with `./sa status <slug>` and `run.md`.

When `progress.full.json` says `"done": true`, run `./sa stage <slug> qa`.
