# Outreach kit — Stage 2

Everything needed to start the institutional conversations that
`MONETIZATION.md` §8b calls the part that actually produces revenue. None of
this is code, and none of it needs accounts, payment or the AI to exist.

| File | What it is |
|---|---|
| `01-email-en.md` | The cold email + two follow-ups, English |
| `02-email-ar.md` | The same three, Arabic |
| `03-objections.md` | Written answers to the questions they will ask |
| `04-targets.md` | Who to write to, and how to find the right person |
| `05-tracker.csv` | Who, when, what happened |
| `06-tracker-guide.md` | How to fill the tracker, and what to read from it after twenty |
| `samples/` | The two `.docx` attachments, ready to send |

---

## ⛔ The one thing blocking the first send

**There is no deployed URL.** The app runs on `127.0.0.1:5000`, which nobody
else can open. Every email below links to the site, and the whole approach
depends on the product demonstrating itself rather than you selling it.

Until there is a public URL, the kit cannot be used. That is a hosting task,
not a development one — Stage 1 is done and the app is deployable
(`CVSTAND_SERVER_STORE=0`, see `BUILD.md`).

Two placeholders appear throughout. Replace both before sending:

- `[LINK]` — the public URL
- `[YOUR NAME]` — how you sign

**The attachments already exist** — `outreach/samples/`:

- `sample-cv-english.docx`
- `sample-cv-arabic.docx`

Both generated from the shipped samples on `modern-t2` and verified: valid
OOXML, no unrendered template tags, and the Arabic one carries real RTL
markup (42 `w:bidi`, 40 `w:rtl`, `bidiVisual` on the chip table). That is the
claim the email makes, so it is worth knowing it is checked rather than
assumed.

**The attachment is the argument; the email is just the covering note.**

⚠ To open them yourself, **copy them out of `Downloads\` first.** This project
lives under Word's default "unsafe locations", so double-clicking a `.docx`
inside it fails with "Office has detected a problem with this file". The file
is fine — see the Protected View note in `RESUME_HERE.md`. Email attachments
are unaffected; this only bites you checking them locally.

Regenerate them any time the templates change:

```
venv/Scripts/python - <<'EOF'
import json, pathlib, sys; sys.path.insert(0, ".")
from app.exporters import render_docx
from app.schema import validate
for name, src in [("sample-cv-english.docx", "data/sample_resume.json"),
                  ("sample-cv-arabic.docx",  "data/sample_resume_ar.json")]:
    d = json.loads(pathlib.Path(src).read_text(encoding="utf-8")); validate(d)
    pathlib.Path("outreach/samples", name).write_bytes(render_docx(d, "modern-t2"))
EOF
```

---

## How to send

**Twenty by hand beats two thousand blasted.** A mail-merge blast is spam: it
burns your sending domain so your *real* email stops arriving, and Saudi has
anti-spam rules worth checking (CITC) before any volume sending. Twenty
personalised emails is one evening's work and is the entire plan.

1. **Send from a real address on your own domain**, not a free webmail account.
   An institution replies to a person at a company.
2. **Personalise one line per email.** Not the whole thing — one line proving
   you looked at them specifically. `04-targets.md` says where to find it.
3. **Five to ten a day, not fifty.** A new domain sending fifty cold emails on
   day one lands in spam folders permanently.
4. **Log every one in `05-tracker.csv` as you send it.** You will not remember.
5. **Follow up twice, then stop.** Days 7 and 21. Silence after that is an
   answer; a fourth email costs you the relationship.

## What NOT to claim

The email only works if every line survives being checked. Do not add:

- **Anything about the AI assistant.** It is not shipped to users and its
  Arabic has not passed Phase 2. Claiming it now is claiming something that
  might not survive review.
- **User numbers, downloads, or "trusted by".** There are none yet. An
  institution that discovers you inflated this will not take a second meeting.
- **A price for institutions.** Not decided (`MONETIZATION.md` §8 says
  "quote"). If they ask, `03-objections.md` has the honest answer.
- **Comparisons naming a competitor as bad.** State what yours does; let them
  draw the conclusion.

## What you are actually offering them

Free use for their students, now. Not a sale. The institutional relationship
is the asset; revenue comes later and is quoted per situation. If the first
email reads as a sales pitch it will be forwarded to procurement and die
there — it should read as a useful thing from someone who built it.
