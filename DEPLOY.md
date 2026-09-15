# Deploying CVStand

Written 2026-09-14. Phases A and B (internal rename, Dockerfile, git repo) are
**done and committed**. Phases C and D need your accounts and are below, in
order, as steps you run.

Nothing here is guesswork about the app: every value comes from `app/config.py`,
`app/limits.py` or `app/__init__.py`, and `.env.example` is the canonical list.

---

## The shape of the thing

| | |
|---|---|
| Domain + mailbox | **Hostinger** (already bought: `cvstand.com`, Starter Business Email) |
| Application | **Railway** (or Render/Fly — same Dockerfile) |
| Why not Hostinger hosting | The PDF export launches a real Chromium per request. Shared/PHP hosting cannot run a persistent Python process or a headless browser. |

Keeping the domain and mailbox at Hostinger while the app runs elsewhere is
normal and is what the DNS step below sets up.

---

## Phase C — Railway

### C1. Push to GitHub — DONE 2026-09-14

`origin` is **https://github.com/Jameel818/cvstand** and `main` is on it.
Nothing secret is committed — verified before the first commit: no `.env`, no
`data/*.db`, no `venv/`.

What remains is keeping it current: **Railway builds what is on GitHub, not
what is on disk.** Before every deploy, check you are not ahead:

```
git status -sb        # "[ahead N]" means Railway would build a stale tree
git push origin main
```

> **A push cannot be run from inside Claude Code.** It needs an interactive
> credential prompt; every attempt hangs. Run it in your own terminal.
> `git -c credential.interactive=never push` fails fast and is the safe way to
> test whether a credential is stored.
>
> Git Credential Manager's device-code flow is broken on this machine — the
> OAuth callback shows "This site can't be reached" and Git never receives the
> token. The fallback is a Personal Access Token (scope `repo`) from
> https://github.com/settings/tokens/new, used once as
> `git push https://TOKEN@github.com/Jameel818/cvstand.git main`.
> **Never let a token into the repo, a file, or a transcript.**

### C2. Create the service

Railway → **New Project** → **Deploy from GitHub repo** → pick the repo.

It will detect the `Dockerfile` and build from it. **Do not** let it pick a
Nixpacks/Python builder — the Dockerfile is what installs Chromium.

First build takes ~5 minutes: it installs Chromium and its system libraries.

### C3. Add the volume FIRST — before anyone signs up

Railway → your service → **Variables/Settings** → **Volumes** → New Volume,
mount path **`/data`**.

**Do this before the first real signup.** A container filesystem is ephemeral.
Without a volume the app works perfectly and then every deploy silently
deletes every account that has ever been created — `app/db.py` puts
`cvstand.db` under `CVSTAND_DATA_DIR`, which the Dockerfile sets to `/data`.

### C4. Set the variables

Copy from `.env.example`. The minimum:

```
SECRET_KEY=<paste a real one>
CVSTAND_SERVER_STORE=0
CVSTAND_DATA_DIR=/data
CVSTAND_TRUSTED_PROXIES=1
CVSTAND_RENDER_CONCURRENCY=1
```

Generate the key locally, never reuse one from anywhere:

```
venv/Scripts/python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**`CVSTAND_SERVER_STORE=0` is the one that must not be wrong.** At the default
`1`, the server keeps ONE résumé at `data/resume.json` and two visitors read
and overwrite each other's document. There is no bug anywhere in the code —
it is one file where there needs to be one per person. `app/config.py` says so
at length.

One way this still bites silently:
- Spelling it `RESUMECRAFT_SERVER_STORE` (the old name, renamed 2026-09-14).
  It is then ignored and the default applies. **A misspelled name is the only
  remaining silent failure** — nothing can distinguish it from "unset".

The value itself is now safe to get wrong loudly rather than quietly:
`app/config.py:_flag` accepts `0/false/no/off` and `1/true/yes/on`, and raises
`AmbiguousFlag` at import on anything else. So `false` means false, and a typo
stops the container instead of silently flipping the setting. (This paragraph
described the old `!= "0"` check; that was replaced the same day the rename
landed.)

If `SECRET_KEY` is missing or still the shipped default while
`CVSTAND_SERVER_STORE=0`, the app **refuses to boot** with
`InsecureDeployment`. That is intended: the session cookie carries who you
are, so a known signing key mints sessions as any user. A container that will
not start is the loud version of that failure.

### C5. Size the instance

Chromium is the memory floor, not Flask. **1 GB minimum**; 512 MB will
OOM-kill under any PDF load. Keep `CVSTAND_RENDER_CONCURRENCY=1` until you
have watched real memory use.

The Dockerfile runs **one gunicorn worker with 8 threads**, deliberately —
`app/limits.py`'s admission semaphore is per-process, so extra workers
multiply the real concurrency cap instead of respecting it. Raising throughput
means moving that state out of memory, not adding workers.

### C6. Smoke-test on the Railway URL, before DNS

Against the `*.up.railway.app` URL:

- [ ] `/` loads, wordmark reads **CVStand**, footer shows `info@cvstand.com`
- [ ] `/templates` shows all 49; switch the language — the UI flips to Arabic RTL
- [ ] `/builder` — type a name, it appears in the preview
- [ ] **Download PDF** — this is the Chromium path and the one most likely to
      fail first in a container
- [ ] **Download Word**
- [ ] `PUT /api/resume` returns **403** (proves `CVSTAND_SERVER_STORE=0` took)
- [ ] Sign up, redeploy, sign in again — proves the volume is mounted
- [ ] `/manifest.webmanifest` returns `"name": "CVStand"`

That PDF check is worth doing twice. If it fails, it is almost always Chromium
not being found — check `PLAYWRIGHT_BROWSERS_PATH=/opt/playwright` survived.

---

## Phase D — DNS at Hostinger

### ⚠ Read this before touching anything

**You just bought email on this domain. DNS is how it works, and DNS is how
you break it.**

Changing the **A** / **CNAME** records points the website somewhere new.
Touching the **MX** or the mail **TXT** records (SPF/DKIM/DMARC) stops mail
being delivered — silently, with senders getting bounces you never see.

So:

1. **Screenshot the whole DNS zone first.** Every record, before any edit.
2. Only ever touch `A` (or `CNAME`) for `@` and `www`.
3. **Never** touch `MX`, or any `TXT` record containing `v=spf1`,
   `v=DMARC1`, or a `._domainkey` name.

### D1. Get the target from Railway

Railway → Settings → **Networking** → Custom Domain → enter `cvstand.com`.
It gives you a CNAME target like `xxxx.up.railway.app`.

### D2. Set the records at Hostinger

Hostinger → **Domains** → cvstand.com → **DNS / Nameservers**:

| Type | Name | Value | Note |
|---|---|---|---|
| CNAME | `www` | `xxxx.up.railway.app` | from Railway |
| A or ALIAS | `@` | as Railway instructs | root domains often cannot CNAME |
| MX | `@` | **leave exactly as-is** | your mailbox |
| TXT | `@` (`v=spf1…`) | **leave exactly as-is** | mail auth |

If Railway asks for a CNAME on the root and Hostinger refuses it, use
Hostinger's ALIAS/ANAME type, or redirect the root to `www`.

Propagation is usually minutes, up to 48h.

### D3. Verify BOTH, not just the website

- [ ] `https://cvstand.com` serves the app, with a valid certificate
- [ ] `https://www.cvstand.com` works too
- [ ] **Send an email to `info@cvstand.com` from another account and confirm it
      arrives.** Do this *after* the DNS change. The website working tells you
      nothing about whether mail still does.

---

## Before you send a single outreach email

`outreach/` is seven templates with `[LINK]` and `[YOUR NAME]` placeholders and
needs no rename — verified. Once the site is live:

1. Create the mailbox `info@cvstand.com` in Hostinger → Emails. **Buying the
   plan is not the same as creating the address**, and the app already links
   to it from every page footer.
2. Fill `[LINK]` with `https://cvstand.com`.
3. Set up **SPF, DKIM and DMARC** in Hostinger's email panel before any cold
   send. A new domain has no sending reputation; without these, mail to Saudi
   and UAE institutions lands in spam.
4. Send a handful, not hundreds. Reputation is built slowly and burned once.

---

## Rollback

Railway keeps previous deployments — redeploy an earlier one from the
dashboard. DNS changes revert by restoring the records from the screenshot in
step D-⚠-1, which is what that screenshot is for.
