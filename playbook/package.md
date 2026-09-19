# Package (autonomous · 20 min) → workbook, email, README, recipient

**Goal:** everything B5 needs to say yes to, passing `./sa check`.

## Start Here (`package/start_here.md`)
Its sections are:
- title
- who it was built for
- what it is
- the headline
- how you could use it (one linked line per use tab)
- how it was built (repo link)
- contact

Every number is a `{{fact:…}}`. Literal non-claims such as `{{lit:24/7}}` are wrapped. Names and
links are `{{var:…}}` from `package.json`.

## The email (`package/email.md`)
- Four to six sentences, in this order:
  1. the hook: the headline finding about *their* world;
  2. what's attached;
  3. "open Start Here first";
  4. the pipe (link, invite note, or "happy to walk you through how it was built");
  5. one ask.
- The subject is specific and carries a fact: *"{{fact:x}} <things> your team hasn't seen yet"*,
  not "Application for …".
- No hype adjectives, no "I'm passionate about". The dataset is the pitch.
- Plain text. The workbook goes as an attachment (≤10 MB); add a zip only for a no-GitHub run
  when Mike chose one.

**Delivery routes**, in order:
1. email the recipient;
2. the ATS form's "additional documents" upload;
3. a link from the cover letter.

## The recipient (`package/recipient.md`, reserve search bucket)
1. **A self-published address:** their site's team or contact page, the posting, a personal site,
   talk pages, a GitHub profile's public email.
2. **Otherwise, the company's pattern:** find **at least one real address at the domain** on the
   public web (press releases, docs, blog bylines, event pages). Infer the pattern (`first@`,
   `first.last@`, `flast@`) and apply it to the recipient's name. Record every evidence URL and
   write **"Pattern-derived: yes, from …"**. No SMTP probing, no paid finders.
3. **Neither:** the ATS upload plus a LinkedIn note, or a generic inbox (`hello@`, `careers@`)
   addressed to the person by name.

## The repo link (`package.json` → `repo_url`)
- **public / private tier:** exactly `https://github.com/<owner>/<niche_slug>`, which is the repo
  `./sa publish` will create. The workbook can therefore carry the final link before anything is
  published.
- **none tier:** leave it empty, and replace the repo-link line in `start_here.md` and `email.md`
  with "Happy to walk you through the pipe that built this." Otherwise the check fails on the
  placeholder link.

## Finish
- Finish `README.tmpl.md` (why this exists, what's hard). No company names.
- In `pipe/`, run `make sheet && make readme`.
- `./sa check <slug>` must pass. Fix what it names, rebuild, re-check.

Then run `./sa stage <slug> b5`.
