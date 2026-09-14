"""The label catalogue: every fixed English string the 49 resume templates
print, and its Arabic counterpart.

Phase 3 of the bilingual work. Before this, ~270 label occurrences in ~50
spellings were hardcoded in the .j2 files, so an Arabic resume rendered Arabic
CONTENT under English HEADINGS.

Three decisions, each made to protect the English output:

1. **The message id IS the English string.** `t('Work Experience')` returns
   'Work Experience' verbatim when the document is English. So English is
   character-identical BY CONSTRUCTION, not because 80 hand-written mappings
   were each checked. The golden HTML gate proves it, but the design is what
   makes the proof cheap: there is no English table to get wrong.

   This is also why the templates' inconsistent phrasing is preserved rather
   than normalised. `Work Experience`, `WORK EXPERIENCE` and `PROFESSIONAL
   EXPERIENCE` stay exactly as each template wrote them.

2. **Lookup folds case and whitespace.** Arabic has no letter case, so the ~40
   casing variants collapse to one Arabic entry each: `SKILLS`, `Skills` and
   `skills` are one row, not three. That keeps the Arabic side at ~50 rows
   instead of ~80 and makes a missing translation obvious.

3. **A missing translation renders English, never raises.** A resume must not
   500 because a label was not translated (the project rule that produced
   `normalize()`'s degrade paths). Coverage is enforced at TEST time instead —
   `tests/test_labels.py` scans the templates and fails on any msgid this
   catalogue does not carry, so the gap is caught in CI rather than in a user's
   PDF.

Why a ContextVar and not `@jinja2.pass_context`
-----------------------------------------------
`t()` needs to know the document language. Reading it from the Jinja context
(`ctx['r'].lang`) works in a template but NOT inside a macro: every template
does `{% import "_macros.j2" as m %}` WITHOUT `with context`, so an imported
macro gets a fresh context in which `r` does not exist. A `pass_context`
version would therefore return English inside any macro that ever used it —
silently, with no error, which is this project's signature failure mode.

`_LANG` is set by `rendering.canvas_html()` around the render and reset after.
A ContextVar is per-thread (and per-task), so Flask's threaded server cannot
leak one request's language into another's.
"""
from __future__ import annotations

from contextvars import ContextVar

from markupsafe import Markup

# Set by rendering.canvas_html() for the duration of one render.
_LANG: ContextVar[str] = ContextVar("resume_lang", default="en")


def _key(text: str) -> str:
    """Lookup key: whitespace-collapsed and case-folded (see decision 2)."""
    return " ".join(text.split()).casefold()


# Msgids whose text carries markup, so `t()` must return Markup rather than let
# autoescape turn the tag into visible text. Deliberately tiny and explicit —
# these are the only three labels in the catalogue that are not plain text, all
# of them two-line headings where the line break sits INSIDE the phrase.
# They cannot be split into two t() calls: Arabic word order differs, so the
# break falls in a different place.
_MARKUP_MSGIDS = frozenset(
    _key(s)
    for s in (
        "PERSONAL<br>INFORMATION",
        "EDUCATION &amp;<br>QUALIFICATIONS",
        "PORTRAIT<br>PLACEHOLDER",
    )
)


# English (folded) -> Arabic.
#
# Grouped by the section they head. Several English spellings intentionally map
# to the same Arabic string where the distinction is only English register
# ("Tools" / "Tooling"); where the distinction is real it is preserved
# ("Location" is a place, "Website" is a URL — both would be "الموقع" if
# translated word-for-word, so the second is disambiguated).
_AR: dict[str, str] = {
    # --- experience -------------------------------------------------------
    "experience": "الخبرة",
    "work experience": "الخبرة العملية",
    "professional experience": "الخبرة المهنية",
    # --- education --------------------------------------------------------
    "education": "التعليم",
    "educational history": "المسيرة التعليمية",
    "education and certifications": "التعليم والشهادات",
    "education, tools & credentials": "التعليم والأدوات والمؤهلات",
    "education &amp;<br>qualifications": "التعليم<br>والمؤهلات",
    # --- skills -----------------------------------------------------------
    "skills": "المهارات",
    "personal skills": "المهارات الشخصية",
    "technical skills": "المهارات التقنية",
    "technical": "التقنيات",
    "creative & technical skills": "المهارات الإبداعية والتقنية",
    "core competencies": "الكفاءات الأساسية",
    "capabilities": "القدرات",
    "expertise": "مجالات الخبرة",
    # --- tools ------------------------------------------------------------
    "tools": "الأدوات",
    "tooling": "الأدوات",
    "software": "البرمجيات",
    "systems": "الأنظمة",
    "studio": "الاستوديو",
    # --- languages --------------------------------------------------------
    "languages": "اللغات",
    "language": "اللغة",
    # --- summary ----------------------------------------------------------
    "summary": "نبذة",
    "professional summary": "نبذة مهنية",
    "profile": "الملف الشخصي",
    "about me": "نبذة عني",
    "career objective": "الهدف المهني",
    # --- credentials ------------------------------------------------------
    "certifications": "الشهادات",
    "training": "التدريب",
    "key achievements": "أبرز الإنجازات",
    "recognition": "التقدير",
    "awards": "الجوائز",
    "references": "المراجع",
    # --- contact ----------------------------------------------------------
    "contact": "التواصل",
    "personal<br>information": "المعلومات<br>الشخصية",
    "email": "البريد الإلكتروني",
    "email:": "البريد الإلكتروني:",
    "phone": "الهاتف",
    "phone:": "الهاتف:",
    "location": "الموقع",
    "address": "العنوان",
    "website": "الموقع الإلكتروني",
    "web": "الويب",
    "portfolio": "الأعمال",
    "link": "الرابط",
    "publications and education": "المنشورات والتعليم",
    "technical stack": "الحزمة التقنية",
    "tools & languages": "الأدوات واللغات",
    "gpa": "المعدل التراكمي",
    "education & certifications": "التعليم والشهادات",
    "tools:": "الأدوات:",
    "languages:": "اللغات:",
    "resume": "سيرة ذاتية",
    # --- misc -------------------------------------------------------------
    "also": "أيضاً",
    "photo": "صورة",
    "portrait<br>placeholder": "صورة<br>شخصية",
}


def t(text: str) -> str:
    """Translate a fixed template label for the document being rendered.

    English (or any untranslated msgid) returns `text` unchanged — see the
    module docstring for why that is the whole English-safety argument.
    """
    out = text if _LANG.get() != "ar" else _AR.get(_key(text), text)
    return Markup(out) if _key(text) in _MARKUP_MSGIDS else out


def set_lang(lang: str):
    """Bind the language for the current render. Returns the ContextVar token;
    pass it to `_LANG.reset()` to restore. `rendering.canvas_html()` owns this.
    """
    return _LANG.set(lang)


def reset_lang(token) -> None:
    _LANG.reset(token)


def translation_for(text: str) -> str | None:
    """The Arabic string for an English msgid, or None. For tests/tooling."""
    return _AR.get(_key(text))


# Conjunction and list separator, per language. Three ATS templates compose a
# trailing catch-all heading from whichever optional sections a resume has
# ("Certifications, Tools & Languages"), so the PUNCTUATION is as
# language-dependent as the words: Arabic joins with an Arabic comma and the
# conjunction "و". Translating only the words would leave "الشهادات, الأدوات &
# اللغات" - half-translated, and in the wrong script for the separator.
_JOIN = {
    "en": {"sep": ", ", "conj": " %s "},
    "ar": {"sep": "، ", "conj": " و "},
}


def join_labels(parts, conj: str = "&") -> str:
    """Join already-translated label words into one composed heading.

    `conj` is the ENGLISH conjunction the template wrote - ats/t4 uses "and"
    where ats/t12 and ats/t14 use "&" - and is honoured verbatim in English so
    the existing output does not move. Arabic ignores it and uses "و" for both,
    because the distinction is an English register choice with no counterpart.
    """
    parts = [p for p in parts if p]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    rules = _JOIN["ar" if _LANG.get() == "ar" else "en"]
    joiner = rules["conj"] if _LANG.get() == "ar" else rules["conj"] % conj
    return rules["sep"].join(parts[:-1]) + joiner + parts[-1]


# ---------------------------------------------------------------------------
# The APP SHELL catalogue (phase 6).
#
# Separate from the document catalogue above, and resolved against a separate
# language, because they answer different questions:
#
#   `t()`      what language is the RESUME written in?  (resume["lang"])
#   `ui_t()`   what language does this PERSON read?     (the ui_lang cookie)
#
# Someone editing an English resume from an Arabic interface is an ordinary
# case, so the two must be able to disagree. That was one of the four
# assumptions recorded when the bilingual plan was written.
#
# Lookup falls through to the document catalogue, which is not a shortcut but
# the point: the builder's section headings ARE the resume's section headings
# ("Experience", "Skills", "Education"), and a person should not see one word
# in the form and a different one on the page.
_UI_AR: dict[str, str] = {
    # --- header / footer chrome ------------------------------------------
    # "CVStand" is the product name and is NOT translated - a brand does
    # not change script when the interface does.
    # Page titles read "<Brand> — <this>", so these are title fragments, not
    # sentences. The brand itself is never translated (see above).
    "Builder": "المنشئ",
    "designer résumés, done in minutes": "سير ذاتية بتصاميم احترافية، جاهزة في دقائق",
    "Build a polished résumé in minutes. 49 designer layouts across Modern and ATS-friendly families. Export to PDF and Word.":
        "أنشئ سيرة ذاتية أنيقة في دقائق. 49 تصميمًا احترافيًا من عائلتَي مودرن والمتوافقة مع أنظمة التتبع. صدّرها إلى PDF وWord.",
    # The tagline. Disambiguates "Stand" -- see app/brand.py. The Arabic is
    # not a literal translation: it says "catches the eye", which carries
    # the stand-out sense with no booth reading available at all.
    "Make your CV stand out.":
        "اجعل سيرتك الذاتية تلفت الأنظار.",
    "Templates": "القوالب",
    "How it works": "كيف يعمل",
    "Families": "العائلات",
    "Build my résumé": "أنشئ سيرتي الذاتية",
    "Designer résumé layouts, your content, exported to PDF and Word.":
        "تصاميم احترافية للسيرة الذاتية، بمحتواك أنت، وتصدير إلى PDF وWord.",
    "Product": "المنتج",
    "All templates": "كل القوالب",
    "Modern family": "عائلة مودرن",
    "ATS-friendly family": "العائلة المتوافقة مع أنظمة التوظيف",
    "Open the builder": "افتح المنشئ",
    "About": "عن التطبيق",
    "FAQ": "الأسئلة الشائعة",
    "Built as a single-user tool. Your résumé stays on this machine.":
        "أداة لمستخدم واحد. سيرتك الذاتية تبقى على هذا الجهاز.",

    # --- landing: hero ----------------------------------------------------
    "Modern & ATS-friendly": "مودرن ومتوافقة مع أنظمة التوظيف",
    "Your résumé,": "سيرتك الذاتية،",
    "designed": "بتصميم احترافي",
    "and done in minutes.": "وجاهزة خلال دقائق.",
    "Fill in your details once. Switch between": "أدخل بياناتك مرة واحدة. تنقّل بين",
    "designer layouts, preview live, and export a pixel-perfect PDF or an editable Word file.":
        "تصميماً احترافياً، وشاهد المعاينة مباشرة، وصدّر ملف PDF بدقة تامة أو ملف Word قابلاً للتحرير.",
    "Start building — it's free": "ابدأ الآن — مجاناً",
    "Browse templates": "تصفّح القوالب",
    "Modern designs": "تصاميم مودرن",
    "ATS-safe designs": "تصاميم متوافقة مع أنظمة التوظيف",
    "PDF + Word export": "تصدير PDF وWord",
    "No sign-up": "بدون تسجيل",
    "Modern layouts": "تصاميم مودرن",
    "ATS-friendly layouts": "تصاميم متوافقة مع أنظمة التوظيف",
    "Export formats": "صيغ التصدير",
    "Content model, every design": "محتوى واحد لكل التصاميم",

    # --- accounts (Stage 3) -----------------------------------------------
    # An account is only needed for the PAID features; the free tier stays
    # sign-up-free, and the intro line below says so in both languages.
    "Sign in": "تسجيل الدخول",
    "Sign out": "تسجيل الخروج",
    "Create your account": "إنشاء حساب",
    "Create account": "إنشاء الحساب",
    "Create one": "أنشئ حساباً",
    "Email": "البريد الإلكتروني",
    "Password": "كلمة المرور",
    "Already have an account?": "لديك حساب بالفعل؟",
    "No account yet?": "ليس لديك حساب؟",
    "You only need an account for the paid features. Building a résumé and downloading a PDF stays free, with no sign-up.":
        "لا تحتاج إلى حساب إلا للمزايا المدفوعة. أما إنشاء السيرة الذاتية وتنزيلها بصيغة PDF فيبقى مجاناً وبلا تسجيل.",
    "At least 10 characters. A short phrase you will remember beats a short password.":
        "١٠ أحرف على الأقل. عبارة قصيرة تتذكّرها خير من كلمة مرور قصيرة.",
    "That email and password do not match.":
        "البريد الإلكتروني وكلمة المرور غير متطابقين.",
    "Forgotten your password? Password reset is not available yet — get in touch and we will sort it out.":
        "نسيت كلمة المرور؟ خاصية الاستعادة غير متاحة بعد — تواصل معنا وسنتولّى الأمر.",

    # Raised by app/auth.py and rendered through t() by account.html. These
    # are msgids, so they must match the raise sites BYTE FOR BYTE — see
    # test_auth.py::test_auth_messages_are_all_translated, which reads them
    # out of the module rather than trusting this list.
    "Enter your email address.": "أدخل بريدك الإلكتروني.",
    "That does not look like an email address.": "هذا لا يبدو بريداً إلكترونياً صحيحاً.",
    "That email address is too long.": "هذا البريد الإلكتروني طويل جداً.",
    "Choose a password.": "اختر كلمة مرور.",
    "Use at least 10 characters — a short phrase is easier to remember and harder to guess than a short password.":
        "استخدم ١٠ أحرف على الأقل — عبارة قصيرة أسهل في التذكّر وأصعب في التخمين من كلمة مرور قصيرة.",
    "Use at least 10 characters.": "استخدم ١٠ أحرف على الأقل.",
    "That password is too long.": "كلمة المرور طويلة جداً.",
    "There is already an account with that email.": "يوجد حساب بهذا البريد الإلكتروني بالفعل.",

    # --- landing: families ------------------------------------------------
    "Two families": "عائلتان",
    "Pick the right tool for where the résumé is going.":
        "اختر ما يناسب الجهة التي سترسل إليها سيرتك الذاتية.",
    "Every layout is fed by the same content, so you can move between them without redoing your work.":
        "كل التصاميم تعتمد المحتوى نفسه، فتنتقل بينها دون إعادة أي عمل.",
    "Modern": "مودرن",
    "Colour, structure, personality": "لون وبنية وشخصية",
    "Two-column designs with sidebars, photos, skill graphics and accent palettes. Built to be sent as a PDF and to stand out in a pile.":
        "تصاميم بعمودين مع أشرطة جانبية وصور ورسوم للمهارات وألوان مميزة. مُعدّة لتُرسل بصيغة PDF ولتلفت النظر بين غيرها.",
    "layouts": "تصميماً",
    "Explore Modern →": "استعرض مودرن ←",
    "ATS-Friendly": "متوافقة مع أنظمة التوظيف",
    "Single column, parse-safe": "عمود واحد، سهلة القراءة آلياً",
    "One clean column, canonical section headings, real text for every skill and level. Made to survive applicant-tracking systems and job-portal uploads.":
        "عمود واحد واضح، وعناوين أقسام قياسية، ونص حقيقي لكل مهارة ومستوى. مُعدّة لتجتاز أنظمة تتبّع المتقدمين وبوابات التوظيف.",
    "Explore ATS →": "استعرض المتوافقة ←",

    # --- landing: why it works --------------------------------------------
    "Why it works": "لماذا ينجح",
    "Everything you need to ship a résumé you're proud of.":
        "كل ما تحتاجه لتخرج بسيرة ذاتية تفخر بها.",
    "Live preview": "معاينة مباشرة",
    "Every keystroke re-renders the page. What you see is exactly what exports.":
        "كل حرف تكتبه يعيد رسم الصفحة. ما تراه هو نفسه ما يُصدَّر.",
    "One content model": "محتوى واحد",
    "Type your experience once. Try it in any of the": "اكتب خبرتك مرة واحدة. جرّبها في أيٍّ من",
    "designs instantly.": "تصميماً فوراً.",
    "ATS-safe option": "خيار متوافق مع أنظمة التوظيف",
    "The ATS family is single-column with parse-safe headings and selectable skill levels.":
        "العائلة المتوافقة بعمود واحد، بعناوين سهلة القراءة آلياً ومستويات مهارات قابلة للتحديد.",
    "PDF & Word": "PDF وWord",
    "Pixel-accurate PDF from a real browser engine, plus an editable .docx.":
        "ملف PDF بدقة تامة من محرك متصفح حقيقي، مع ملف ‎.docx‎ قابل للتحرير.",
    "Photo support": "دعم الصور",
    "Drop in a headshot — it's cropped square and placed cleanly where the design expects it.":
        "أضف صورتك الشخصية — تُقصّ مربّعة وتوضع بدقة حيث يتوقعها التصميم.",
    "Nothing to lose": "لا شيء يضيع",
    "Your résumé is saved locally and reloads where you left off. No account, no upload.":
        "سيرتك الذاتية تُحفظ محلياً وتُفتح من حيث توقفت. بلا حساب وبلا رفع.",

    # --- landing: three steps ---------------------------------------------
    "Three steps": "ثلاث خطوات",
    "From blank to finished in one sitting.": "من صفحة فارغة إلى سيرة مكتملة في جلسة واحدة.",
    "Add your details": "أضف بياناتك",
    "Work through the guided sections — contact, experience, skills, education. Add and reorder entries as you go.":
        "امضِ في الأقسام الموجّهة — التواصل والخبرة والمهارات والتعليم. أضف المدخلات ورتّبها كما تشاء.",
    "Choose a design": "اختر تصميماً",
    "Open the template drawer and switch families or layouts. Your content flows into each one automatically.":
        "افتح لوحة القوالب وبدّل بين العائلات أو التصاميم. ينتقل محتواك إلى كلٍّ منها تلقائياً.",
    "Download": "تنزيل",
    "Export a PDF for sending, or a Word file for portals that ask for one. Come back and tweak anytime.":
        "صدّر ملف PDF للإرسال، أو ملف Word للبوابات التي تطلبه. وعُد للتعديل متى شئت.",

    # --- landing: FAQ -----------------------------------------------------
    "Questions": "أسئلة",
    "Good to know.": "معلومات مفيدة.",
    "Which family should I use?": "أي عائلة أستخدم؟",
    "Send a": "أرسل تصميم",
    "layout as a PDF when a human will read it first — recruiters, referrals, portfolios. Use an":
        "بصيغة PDF حين يقرأه إنسان أولاً — مسؤولو التوظيف والترشيحات وملفات الأعمال. واستخدم تصميم",
    "layout when you're pasting into a job portal or know the résumé is machine-screened before anyone sees it.":
        "حين تلصق سيرتك في بوابة توظيف أو تعلم أنها ستُفحص آلياً قبل أن يراها أحد.",
    "Is the Word export the same as the PDF?": "هل تصدير Word مطابق لملف PDF؟",
    "It preserves the palette, type pairing, section order and skill levels, but Word can't reproduce every visual detail (gradient rings become dot grids, some spacing shifts). The PDF is the pixel-accurate version.":
        "يحافظ على الألوان واقتران الخطوط وترتيب الأقسام ومستويات المهارات، لكن Word لا يستطيع إعادة إنتاج كل تفصيل بصري (الحلقات المتدرجة تصبح شبكات نقاط، وتتغير بعض المسافات). ملف PDF هو النسخة الدقيقة تماماً.",
    "Do you store my résumé?": "هل تحتفظون بسيرتي الذاتية؟",
    "No. It's a single-user tool — your data is a JSON file on this machine and never leaves it.":
        "لا. إنها أداة لمستخدم واحد — بياناتك ملف JSON على هذا الجهاز ولا يغادره أبداً.",
    "Can I use my own photo?": "هل يمكنني استخدام صورتي؟",
    "Yes, on the Modern layouts that include a photo. It's cropped to a square and resized on upload.":
        "نعم، في تصاميم مودرن التي تتضمن صورة. تُقصّ مربّعة ويُعدَّل حجمها عند الرفع.",
    "Build your résumé now.": "أنشئ سيرتك الذاتية الآن.",
    "No sign-up, no paywall. Open the builder, add your details, and download in minutes.":
        "بلا تسجيل وبلا اشتراك. افتح المنشئ، وأضف بياناتك، ونزّلها خلال دقائق.",

    # --- gallery ----------------------------------------------------------
    "Modern templates": "قوالب مودرن",
    "ATS-friendly templates": "القوالب المتوافقة مع أنظمة التوظيف",
    "Colour, sidebars and skill graphics. Best sent as a PDF.":
        "ألوان وأشرطة جانبية ورسوم للمهارات. الأفضل إرسالها بصيغة PDF.",
    "Single column, parse-safe headings, selectable skill levels. Best for job portals.":
        "عمود واحد، وعناوين سهلة القراءة آلياً، ومستويات مهارات قابلة للتحديد. الأنسب لبوابات التوظيف.",
    "Two families, one content model. Pick a layout to open it in the builder.":
        "عائلتان ومحتوى واحد. اختر تصميماً لفتحه في المنشئ.",
    "All": "الكل",
    "Soon": "قريباً",
    "Preview coming soon": "المعاينة قريباً",
    "Selected": "محدَّد",
    "Use this": "استخدم هذا",
    "Coming soon": "قريباً",
    "preview": "معاينة",

    # --- builder chrome ---------------------------------------------------
    "Saved": "تم الحفظ",
    "Saving…": "جارٍ الحفظ…",
    "Unsaved changes": "تغييرات غير محفوظة",
    "PDF": "PDF",
    "Pixel-accurate, for sending": "بدقة تامة، للإرسال",
    "Word (.docx)": "‎Word (.docx)‎",
    "Editable, for job portals": "قابل للتحرير، لبوابات التوظيف",
    "Fill in what applies. Empty sections are hidden from the résumé automatically.":
        "املأ ما ينطبق عليك. الأقسام الفارغة تُخفى من السيرة تلقائياً.",
    "Fit": "ملاءمة",
    "Content runs past one page — trim to fit, or pick a denser layout.":
        "المحتوى يتجاوز صفحة واحدة — اختصره ليناسبها، أو اختر تصميماً أكثر كثافة.",
    "Choose a template": "اختر قالباً",
    "Zoom in": "تكبير",
    "Zoom out": "تصغير",
    "Résumé preview": "معاينة السيرة الذاتية",
    "Close": "إغلاق",
    "Language": "اللغة",

    # --- builder form: sections and fields --------------------------------
    # Anything not here falls through to the DOCUMENT catalogue, which is the
    # point: the form's section names are the resume's section headings.
    "Basics": "الأساسيات",
    "Stat chips": "بطاقات الأرقام",
    "Up to 4 appear on the résumé. A blank metric hides the whole chip.":
        "تظهر أربع بطاقات كحد أقصى. القيمة الفارغة تخفي البطاقة كاملة.",
    "The level word shows as text and as a 5-dot level.":
        "كلمة المستوى تظهر كنص وكخمس نقاط.",
    "Must appear word-for-word in the summary above":
        "يجب أن تظهر حرفياً في النبذة أعلاه",
    "Full name": "الاسم الكامل",
    "Headline / role": "المسمى الوظيفي",
    "Professional summary": "نبذة مهنية",
    "Phrase to highlight": "عبارة للتمييز",
    "Photo": "الصورة",
    "Social link": "رابط اجتماعي",
    "Label": "التسمية",
    "URL": "الرابط",
    "Stat": "رقم",
    "Metric": "القيمة",
    "Caption": "الوصف",
    "Role": "الوظيفة",
    "Job title": "المسمى الوظيفي",
    "Company": "الشركة",
    "Start": "من",
    "End": "إلى",
    "Qualification": "المؤهل",
    "Degree": "الدرجة",
    "School": "المؤسسة التعليمية",
    "Award": "جائزة",
    "Title": "العنوان",
    "Detail": "التفاصيل",
    "Skill": "مهارة",
    "Level": "المستوى",
    "Percent (bars/rings only)": "النسبة (للأشرطة والحلقات فقط)",
    "Tool": "أداة",
    "Reference": "مُعرِّف",
    "Name": "الاسم",
    # --- builder: example placeholders --------------------------------
    "Wren Ashworth": "ورين آشورث",
    "Creative Lead": "مديرة إبداعية",
    "Budget owned": "الميزانية المُدارة",

    # --- builder: status, errors and alerts ---------------------------
    "Modern": "مودرن",
    "ATS-Friendly": "متوافقة مع أنظمة التوظيف",
    "Invalid résumé data.": "بيانات السيرة الذاتية غير صالحة.",
    "Could not reach the preview service.": "تعذّر الوصول إلى خدمة المعاينة.",
    "The preview could not be built (server error ": "تعذّر إنشاء المعاينة (خطأ في الخادم ",
    "The photo could not be uploaded (error ": "تعذّر رفع الصورة (خطأ ",
    "The photo could not be uploaded — the server did not answer.":
        "تعذّر رفع الصورة — لم يستجب الخادم.",
    # The template choice lives in localStorage now, so the way a switch fails
    # is no longer "the server said no" — it is a browser that stores nothing
    # (a private window, or site data blocked).
    "The template could not be switched — this browser is not storing anything.":
        "تعذّر تغيير القالب — هذا المتصفح لا يحفظ أي بيانات.",
    # Shown instead of the single-user line when the server keeps no résumé
    # (CVSTAND_SERVER_STORE=0). Not a slogan — it is literally what the
    # deployed app does, and in this market it is worth saying plainly.
    "Your résumé stays in your browser. It is never stored on our server.":
        "تبقى سيرتك الذاتية في متصفحك. ولا تُحفظ على خادمنا إطلاقاً.",
    # The install manifest's description. "CVStand" itself is deliberately
    # NOT in the catalogue: a brand names itself the same way in both
    # languages, like the language switcher's own labels above.
    "Build a résumé in minutes — 49 designer layouts, PDF and Word.":
        "أنشئ سيرتك الذاتية في دقائق — ٤٩ تصميماً احترافياً، بصيغتَي PDF وWord.",
    "Content still runs past one page after auto-fit — trim it, or pick a denser layout.":
        "المحتوى ما زال يتجاوز صفحة واحدة بعد الملاءمة التلقائية — اختصره أو اختر تصميماً أكثر كثافة.",
    "Auto-fitted to one page — spacing tightened ":
        "تمت الملاءمة في صفحة واحدة — قُلّصت المسافات بنسبة ",
    "Fix to update preview:": "صحّح ما يلي لتحديث المعاينة:",
    "Could not download the ": "تعذّر تنزيل ",
    " export failed.": " فشل التصدير.",
    "Add": "إضافة",
    "Remove": "حذف",

    # --- builder: the DOCUMENT's language (not the interface's) -------------
    # The option labels are autonyms ("English", "العربية"), like the header
    # switcher's, so they are not in the catalogue: a language names itself the
    # same way whoever is reading.
    "Résumé language": "لغة السيرة الذاتية",
    "The language the résumé is written in — sets its direction, its headings and its level words. Not the interface language.":
        "اللغة التي كُتبت بها السيرة الذاتية — تحدد اتجاهها وعناوين أقسامها وكلمات المستوى فيها. وهي ليست لغة الواجهة.",
    "Translate the level words already chosen? ":
        "هل تريد ترجمة كلمات المستوى المختارة مسبقاً؟ ",
}


def _as_html(text: str) -> Markup:
    """Escape a catalogue string the way HTML text is escaped - and no further.

    Jinja's autoescape also turns `'` into `&#39;` and `"` into `&#34;`, which
    is correct for untrusted data and wrong here: these strings are OUR OWN, and
    escaping the apostrophe in "it's free" changes the shell's bytes for no
    safety gain. So `&`, `<`, `>` and `"` are escaped (the first three for text
    nodes, `"` so the result is also safe inside a double-quoted attribute) and
    the apostrophe is left alone.

    Only ever applied to a string that IS in the catalogue - i.e. one this
    project wrote. An unknown msgid falls through to normal autoescaping.
    """
    return Markup(text.replace("&", "&amp;").replace("<", "&lt;")
                      .replace(">", "&gt;").replace('"', "&quot;"))


def ui_t(text: str, lang: str = "en") -> str:
    """Translate an app-shell string for the reader's interface language.

    Falls through to the document catalogue so a form label and the heading it
    produces cannot disagree. Like `t()`, an untranslated string renders in
    English rather than raising - the interface must not 500 over a missing
    label - and coverage is enforced by tests instead.
    """
    key = _key(text)
    known = text in _UI_AR or key in _UI_AR or key in _AR
    if lang != "ar":
        return _as_html(text) if known else text
    out = _UI_AR.get(text) or _UI_AR.get(key) or _AR.get(key)
    return _as_html(out) if out else (_as_html(text) if known else text)


def ui_catalogue(lang: str) -> dict[str, str]:
    """Every shell string in one dict, for handing to builder.js.

    The form is generated in the browser, so its labels cannot go through a
    Jinja call; the page ships the table instead. Built from the SAME source as
    `ui_t`, so the two can never drift.

    Keyed by the FOLDED msgid, and the client folds before looking up. The two
    catalogues are cased differently - `_UI_AR` holds the string as written
    ("Full name") while `_AR` holds it folded ("contact") - so a table keyed by
    either one alone misses half its entries. That is not hypothetical: it
    shipped for one render, and the builder's Contact section stayed in English
    while Basics translated.

    English returns an EMPTY table on purpose. The msgid IS the English string,
    so there is nothing to look up, and shipping an identity mapping would only
    create a second place for English to drift.
    """
    if lang == "en":
        return {}
    out: dict[str, str] = {}
    for src in (_AR, _UI_AR):
        for k in src:
            out[_key(k)] = ui_t(k, lang)
    return out


# ---------------------------------------------------------------------------
# Level vocabularies, per DOCUMENT language.
#
# These are not interface strings: whatever the user picks is STORED in
# `skills[].level` / `languages[].level` and printed on the resume, so they
# follow the document's language, not the reader's. Someone writing an English
# resume from an Arabic interface must not end up with an Arabic level word on
# an otherwise English page.
#
# Split into two lists, which the builder previously did not do. It offered one
# combined list of eight, so a SKILL could be set to "Fluent" - a word
# `LEVEL_DOTS` does not map, which is not "unrated" either, so the macros drew a
# five-dot row with zero filled: a graphic asserting "none" beside the word
# "Fluent". Separating them makes that unreachable from the UI. (Data already
# stored that way is untouched; see RESUME_HERE.md.)
#
# The skill words are exactly `schema.LEVEL_DOTS`'s keys in each language, so a
# level picked here always maps to a dot count.
SKILL_LEVELS = {
    "en": ["Expert", "Advanced", "Proficient", "Foundational"],
    "ar": ["خبير", "متقدم", "متمكن", "أساسي"],
}

LANGUAGE_LEVELS = {
    "en": ["Native", "Fluent", "Conversational", "Basic"],
    "ar": ["اللغة الأم", "بطلاقة", "محادثة", "أساسي"],
}


def levels_for(lang: str) -> dict[str, list[str]]:
    lang = lang if lang in SKILL_LEVELS else "en"
    return {"skill": SKILL_LEVELS[lang], "language": LANGUAGE_LEVELS[lang]}


def all_levels() -> dict[str, dict[str, list[str]]]:
    """Every document language's vocabularies at once, for builder.js.

    `levels_for()` answers "what words does THIS document offer" and is what
    the form's dropdowns are built from. This answers a different question:
    when the user changes the document's language in the builder, the page has
    to re-offer the OTHER language's words - and translate the ones already
    stored - without a round trip.

    The translation is positional: the two lists in a pair are the same length
    and ordered strongest-first in both languages, so index i means the same
    level in either. `tests/test_document_language.py` gates that invariant,
    because it is the only thing making the client-side remap correct.
    """
    return {lang: levels_for(lang) for lang in SKILL_LEVELS}
