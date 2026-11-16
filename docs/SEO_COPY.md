# CVStand — search copy (AR + EN)

What search engines and link previews show for each public page. The live
strings are in `app/labels.py` (`_UI_AR`, under "search: page titles, meta
descriptions"); the English is the msgid in the page template. **Change both
together**: an edit here alone changes nothing on the site.

Every title ends in `| CVStand` (tests/test_brand.py requires the brand in
every `<title>`). Arabic is written for what Arabic searchers type
(سيرة ذاتية، نموذج، قوالب), not translated word for word.

**Numbers are never typed.** `{total}` is the template count from
`app/registry.py` (`registry.counts()`, 49 on 2026-11-16). `{price}` is the
lowest pass price from `app/pricing.py`. In Arabic, `{total_ar}` is the count
with its counted noun in the right form (`pricing.ar_count`: «49 قالباً»). The
`fill` filter puts the values in after translation. `tests/test_pricing.py`
fails if a price is written anywhere else.

**Two states.** `CVSTAND_PAYMENTS_LIVE` (`app/config.py`, default 0) decides
which copy is served. While it is 0, no page names a price or a pass, and no
page promises a free download or "no sign-up". The copy is neutral.

## Titles

| Page | URL | English | العربية |
|---|---|---|---|
| Landing | `/` | CV Maker – Designer & ATS-Friendly Templates \| CVStand | إنشاء سيرة ذاتية احترافية بالعربي والإنجليزي \| CVStand |
| Gallery: all | `/templates` | CV Templates – {total} Modern & ATS Designs \| CVStand | نماذج سيرة ذاتية جاهزة – {total_ar} \| CVStand |
| Gallery: ATS | `/templates?cat=ats` | ATS CV Templates That Pass Screening \| CVStand | قوالب سيرة ذاتية متوافقة مع ATS \| CVStand |
| Gallery: Modern | `/templates?cat=modern` | Modern CV Templates – Designer Layouts \| CVStand | قوالب سيرة ذاتية حديثة بتصميم احترافي \| CVStand |
| Builder | `/builder` | CV Builder – Write, Preview, Export PDF & Word \| CVStand | صانع السيرة الذاتية – PDF و Word \| CVStand |
| Pricing (live only) | `/pricing` | CV Maker Pricing – Passes from {price} \| CVStand | أسعار إنشاء السيرة الذاتية – باقات تبدأ من {price} \| CVStand |
| Sign in / up | `/account/…` | unchanged (never indexed) | unchanged (never indexed) |

`/pricing` is a 404 and is left out of the sitemap while payments are off.

## Meta descriptions

The landing description is also the site-wide default (`base.html`); the
sign-in, sign-up and error pages inherit it but are never indexed.

**Landing / site-wide, payments OFF**
- EN: Build a polished CV in minutes — in English or Arabic. {total} designer and ATS-friendly templates, with PDF and Word download.
- AR: أنشئ سيرتك الذاتية بالعربي أو بالإنجليزي خلال دقائق. {total_ar} بين تصاميم احترافية وقوالب متوافقة مع أنظمة ATS، مع التحميل بصيغتي PDF و Word.

**Landing / site-wide, payments ON**
- EN: Build a polished CV in minutes — in English or Arabic. {total} designer and ATS-friendly templates. Download PDF and Word from {price}.
- AR: أنشئ سيرتك الذاتية بالعربي أو بالإنجليزي خلال دقائق. {total_ar} بين تصاميم احترافية وقوالب متوافقة مع أنظمة ATS، وتحميل PDF و Word ابتداءً من {price}.

**Gallery: all**
- EN: Browse {total} ready-made CV templates — modern designer layouts and clean ATS formats. Pick one and fill it in online.
- AR: تصفّح {total_ar} للسيرة الذاتية: تصاميم حديثة وقوالب ATS بسيطة. اختر قالباً واملأه مباشرة.

**Gallery: ATS**
- EN: Single-column CV templates built to be read by applicant tracking systems. Clean structure, real text, PDF and Word export.
- AR: قوالب سيرة ذاتية بعمود واحد تقرأها أنظمة تتبّع المتقدمين (ATS) بسهولة، مع تصدير PDF و Word.

**Gallery: Modern**
- EN: Designer CV templates with skill graphics and clear hierarchy, in English or Arabic, ready to fill in and export.
- AR: قوالب سيرة ذاتية بتصميم احترافي ورسوم للمهارات، بالعربي أو بالإنجليزي، جاهزة للتعبئة والتصدير.

**Builder**
- EN: Write your CV and cover letter side by side with a live preview, then download as PDF or Word.
- AR: اكتب سيرتك الذاتية ورسالة التغطية مع معاينة فورية، ثم حمّلها بصيغة PDF أو Word.

**Pricing (payments ON only)**
- EN: Day, week or month pass. All {total} CV templates, PDF and Word downloads, Arabic and English. No subscription, no auto-renewal.
- AR: باقة يوم أو أسبوع أو شهر: جميع القوالب الـ{total}، وتحميل PDF و Word، بالعربية والإنجليزية. بلا اشتراك ولا تجديد تلقائي.

## Structured data

The landing page's JSON-LD (`seo.structured_data`) carries `offers` only while
payments are on: the three passes from `pricing.PLANS`, in USD, each with its
duration. While payments are off there are no offers at all, never a price of 0.

## Headings

Visible H1/H2s are unchanged except the landing hero while payments are ON
("Your professional CV — starting at just {price}", «سيرتك الذاتية الاحترافية —
ابتداءً من دولار واحد فقط»). The Arabic hero is outlined artwork, so its price
words are rebuilt with `tools/outline_text.py --build-hero` whenever
`pricing.PLANS` changes; `tests/test_hero_outline.py` fails until then.

| Page | Element | English | العربية |
|---|---|---|---|
| Builder | `<h1 class="sr-only">` (visually hidden) | CV builder | منشئ السيرة الذاتية |
| Pricing | `<h1>` | One payment. No subscription. | دفعة واحدة. بلا اشتراك. |

## Claims to keep true

- **Counts** come from the registry; nothing to update by hand.
- **Prices** come from `app/pricing.py`; nothing to update by hand except
  re-running `--build-hero` (above).
- **"Free"** appears only with payments ON, and only as "build and preview for
  free", which is true. No page says the download is free or needs no sign-up.

## Social preview

`og:image` is `static/icons/og-image.png` (1200×630) and `twitter:image` is
`static/icons/twitter-card.png` (1200×600). Both are copied from
`brand-kits/cvstand-aligned-sw12-gap24_6-r14-11/social/`. `og:title` and
`og:description` repeat the page's title and description above.
