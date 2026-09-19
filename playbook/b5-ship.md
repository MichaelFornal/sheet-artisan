# B5 · Ship review (live · 15 min) → go / no-go

**Goal:** Mike sees exactly what will leave the machine, edits it, and says go, or doesn't.

## Prepare
- `./sa check <slug> --tier <tier>`: every line PASS.
- `./sa publish <slug> --tier <tier>`: the dry run. It stages to `runs/<slug>/publish/<tier>/`,
  strips private sources in the public tier, and scans. Nothing leaves the machine.

## Present
1. The workbook, opened for him: `open runs/<slug>/out/<name>.xlsx`.
2. The rendered email, `out/email.md`, in chat.
3. The recipient, route and evidence from `package/recipient.md`, flagging a pattern-derived
   address.
4. The publish plan: repo name and visibility, file count, what was withheld, sample rows, scan
   result.
5. The README's two hand-written sections.

## Ask
1. Edits to the email, Start Here or README? (Apply them, `make sheet && make readme`, re-check.)
2. Final tier? Options are only those the sensitivity allows:
   - **public:** the niche-named repo; the company is never named.
   - **private:** Mike invites the recipient by email; guests on a personal repo get **write**
     access.
   - **none:** no GitHub, optionally a scanned zip.
3. Go or no-go to publish?

## On "go"
- `./sa publish <slug> --tier <tier> [--zip] --go`
- **Private tier:** tell Mike to invite the recipient at
  `https://github.com/<owner>/<repo>/settings/access` by email. The invitee needs a GitHub account.
- **Mike sends the email himself**, with the workbook attached. Never send it, and never draft it
  into his mailbox unless he asks.
- When he confirms it's sent: `./sa decide <slug> sent "<date> via <route>"`.

Then run `./sa stage <slug> retro`.
