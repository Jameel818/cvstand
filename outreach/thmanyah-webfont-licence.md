# Webfont licence request — thmanyah

Send from your own address to **ask@thmanyah.com**. Their licence invites this
explicitly: *"For license exceptions, extended rights, or customized use cases
not expressly stated in this License, please contact the Company at
ask@thmanyah.com."*

Why it is needed: the licence permits commercial use in websites and permits
embedding *"only as part of a compiled, packaged, or obfuscated product"*, and
separately prohibits making the font *"available in any manner that allows end
users... to extract, download, access... independently as font files, including
through web embedding."* A `@font-face` rule serving a `.woff2` is the second
case. A one-domain webfont grant resolves it.

---

**Subject:** Webfont licence request — thmanyah Sans on cvstand.com

السلام عليكم ورحمة الله وبركاته،

I am the developer of **CVStand** (https://cvstand.com), a bilingual
Arabic/English CV builder. I would like to use **thmanyah Sans** as the Arabic
typeface for the résumé templates and would like to request permission for web
embedding.

I have read the licence carefully. I understand that commercial use in websites
is permitted, and that embedding in a web product is permitted *only as part of
a compiled, packaged, or obfuscated product* — while making the font available
in a way that lets end users extract or download it independently, including
through web embedding, is prohibited. Serving a `.woff2` via `@font-face` falls
under that prohibition, which is why I am writing rather than proceeding.

**What I would like permission for**

- Serving a **subsetted** thmanyah Sans as `.woff2` from the single domain
  `cvstand.com`, for rendering résumé text in the browser preview.
- Embedding a subset in the **PDF exports** users generate from their own CV.

**What I am committing to**

- The font is served only from `cvstand.com`; no other domain, no CDN, no
  public directory listing.
- Subset to the glyphs the product actually renders, not the full font.
- No modification, renaming, or derivative work of any kind.
- Copyright and identifying marks left intact.
- Attribution to thmanyah wherever you would like it — a credit line in the
  site footer and in the licences page is no trouble.
- If you prefer, I will restrict it to the PDF export only and use a different
  face in the browser.

**About the product**

CVStand is a small independent product aimed mainly at Arabic-speaking job
seekers in the Gulf. Getting the Arabic typography right matters more here than
almost anything else — a CV is judged on how it reads. thmanyah Sans is the
best Arabic text face I have found for this, which is why I am asking rather
than settling for something else.

I am happy to pay a licence fee if one applies, and to sign whatever agreement
you use.

شاكرًا لكم حسن تعاونكم،

**[your name]**
CVStand — https://cvstand.com
[your email]

---

## If they say yes

Keep the grant **in writing** and commit it to `outreach/` alongside this file,
so the next person to touch the font pipeline can see the basis for it. Then:

1. Subset the face to the glyphs actually rendered.
2. Wire it into `tools/fetch_fonts_ar.py` the way Cairo and Tajawal already are
   — aliased under the Latin family names with a `unicode-range` confining it
   to Arabic codepoints, so no template changes.
3. Regenerate the pixel baselines deliberately; Arabic metrics will move.

## If they say no, or do not reply

Cairo stays. The specimen at the time measured them as close at CV sizes, and
Cairo is OFL with no restriction of any kind.
