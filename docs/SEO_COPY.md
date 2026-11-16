# CVStand — search copy (AR + EN)

What search engines and link previews show for each public page. The live
strings are in `app/labels.py` (`_UI_AR`, under "search: page titles, meta
descriptions"); the English is the msgid in the page template. **Change both
together**: an edit here alone changes nothing on the site.

Every title ends in `| CVStand` (tests/test_brand.py requires the brand in
every `<title>`). Arabic is written for what Arabic searchers type
(سيرة ذاتية، نموذج، قوالب), not translated word for word.

## Titles

| Page | URL | English | العربية |
|---|---|---|---|
| Landing | `/` | CV Maker – Designer & ATS-Friendly Templates \| CVStand | إنشاء سيرة ذاتية احترافية بالعربي والإنجليزي \| CVStand |
| Gallery: all | `/templates` | CV Templates – 49 Modern & ATS Designs \| CVStand | نماذج سيرة ذاتية جاهزة – 49 قالباً \| CVStand |
| Gallery: ATS | `/templates?cat=ats` | ATS CV Templates That Pass Screening \| CVStand | قوالب سيرة ذاتية متوافقة مع ATS \| CVStand |
| Gallery: Modern | `/templates?cat=modern` | Modern CV Templates – Designer Layouts \| CVStand | قوالب سيرة ذاتية حديثة بتصميم احترافي \| CVStand |
| Builder | `/builder` | CV Builder – Write, Preview, Export PDF & Word \| CVStand | صانع السيرة الذاتية – PDF و Word \| CVStand |
| Sign in / up | `/account/…` | unchanged (never indexed) | unchanged (never indexed) |

## Meta descriptions

The landing description is also the site-wide default (`base.html`); the
sign-in, sign-up and error pages inherit it but are never indexed.

**Landing**
- EN: Build a polished CV in minutes — in English or Arabic. 49 designer and ATS-friendly templates. Free PDF download, Word export too.
- AR: أنشئ سيرتك الذاتية بالعربي أو بالإنجليزي خلال دقائق. 49 قالباً احترافياً ومتوافقاً مع أنظمة ATS، وتحميل مجاني بصيغة PDF وتصدير إلى Word.

**Gallery: all**
- EN: Browse 49 ready-made CV templates — modern designer layouts and clean ATS formats. Pick one and fill it in online.
- AR: تصفّح 49 نموذج سيرة ذاتية جاهزاً: تصاميم حديثة وقوالب ATS بسيطة. اختر قالباً واملأه مباشرة.

**Gallery: ATS**
- EN: Single-column CV templates built to be read by applicant tracking systems. Clean structure, real text, PDF and Word export.
- AR: قوالب سيرة ذاتية بعمود واحد تقرأها أنظمة تتبّع المتقدمين (ATS) بسهولة، مع تصدير PDF و Word.

**Gallery: Modern**
- EN: Designer CV templates with skill graphics and clear hierarchy, in English or Arabic, ready to fill in and export.
- AR: قوالب سيرة ذاتية بتصميم احترافي ورسوم للمهارات، بالعربي أو بالإنجليزي، جاهزة للتعبئة والتصدير.

**Builder**
- EN: Write your CV and cover letter side by side with a live preview, then download as PDF or Word.
- AR: اكتب سيرتك الذاتية ورسالة التغطية مع معاينة فورية، ثم حمّلها بصيغة PDF أو Word.

## Headings

Visible H1/H2s are unchanged: they are the brand voice, and the Arabic hero
and gallery H1s are outlined artwork. One addition:

| Page | Element | English | العربية |
|---|---|---|---|
| Builder | `<h1 class="sr-only">` (visually hidden) | CV builder | منشئ السيرة الذاتية |

## Claims to keep true

- **"49"** = 24 Modern + 25 ATS templates (2026-11-16). It is written into
  four strings, so update all four if the count changes.
- **"Free"** applies to building and the PDF download only
  (`account.html`). The copy never says Word export is free.

## Social preview

`og:image` is `static/icons/og-image.png` (1200×630) and `twitter:image` is
`static/icons/twitter-card.png` (1200×600). Both are copied from
`brand-kits/cvstand-aligned-sw12-gap24_6-r14-11/social/`. `og:title` and
`og:description` repeat the page's title and description above.
