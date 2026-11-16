"""Pricing copy: one source of truth, and a switch that hides ALL of it.

What has to stay true (user, 2026-11-16):

* PRICES come only from app/pricing.py (PLANS). No template, catalogue row,
  script or stylesheet states one. Changing PLANS changes every page.
* TEMPLATE COUNTS come only from app/registry.py.
* PAYMENTS_LIVE OFF (the default): no price, no pass wording, no pricing nav
  link, /pricing is a 404, no pass FAQ, no JSON-LD offers, and no
  "free download" / "no sign-up" promise either.
* PAYMENTS_LIVE ON: the full pricing copy, in Arabic and English.
* The FAQ says honestly where the CV is stored, in both store modes.

Every client states its language with ?lang=, because a visitor with no
signal is served Arabic (i18n.NO_SIGNAL_UI_LANG).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app import create_app, pricing, registry

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["/", "/templates", "/templates?cat=modern", "/templates?cat=ats",
         "/builder", "/account/sign-in", "/account/sign-up"]
LANGS = ("en", "ar")


def _client(live: bool):
    app = create_app()
    app.config.update(TESTING=True, PAYMENTS_LIVE=live)
    return app.test_client()


def _get(client, path, lang):
    sep = "&" if "?" in path else "?"
    return client.get(f"{path}{sep}lang={lang}")


def _visible(html: str) -> str:
    """Everything a reader or a crawler gets: text plus the head's meta and
    JSON-LD. Scripts other than JSON-LD are dropped (the builder's catalogue
    is data, not copy)."""
    html = re.sub(r'<script(?![^>]*ld\+json)[^>]*>.*?</script>', " ", html, flags=re.S)
    return html


def _jsonld(html: str) -> dict:
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    assert m, "no JSON-LD on the landing page"
    return json.loads(m.group(1))


# ---------------------------------------------------------------- the source

def test_the_plans_are_what_the_user_set():
    got = [(p.id, p.price_usd, p.days, p.popular) for p in pricing.PLANS]
    assert got == [("day", 1, 1, False), ("week", 3, 7, True), ("month", 7, 30, False)]
    assert pricing.AUTO_RENEW is False and pricing.CURRENCY == "USD"


def test_the_switch_defaults_off():
    assert create_app().config["PAYMENTS_LIVE"] is False


def test_price_formatting():
    assert pricing.fmt_usd(1) == "$1" and pricing.fmt_usd(1, "ar") == "1$"
    assert pricing.fmt_usd(3 / 7) == "$0.43" and pricing.fmt_usd(7 / 30) == "$0.23"


@pytest.mark.parametrize("n,expected", [
    (1, "قالب عصري واحد"), (2, "قالبان عصريان"), (3, "3 قوالب عصرية"),
    (10, "10 قوالب عصرية"), (11, "11 قالباً عصرياً"), (24, "24 قالباً عصرياً"),
    (25, "25 قالباً عصرياً"), (99, "99 قالباً عصرياً"), (100, "100 قالب عصري"),
    (103, "103 قوالب عصرية"), (111, "111 قالباً عصرياً"),
])
def test_arabic_number_agreement(n, expected):
    assert pricing.ar_count(n, pricing.AR_MODERN) == expected


def test_arabic_durations():
    week, month = pricing.PLANS[1], pricing.PLANS[2]
    assert pricing.duration(pricing.PLANS[0], "ar") == "24 ساعة"
    assert pricing.duration(week, "ar") == "7 أيام"
    assert pricing.duration(month, "ar") == "30 يوماً"
    assert pricing.duration(month, "en") == "30 days"


# Literal prices anywhere a reader-facing string could hide. The generated
# Arabic hero is checked by test_hero_outline (its words come from pricing).
# A price is a small whole dollar amount ("$1", "3$") or a per-day figure;
# "$3.2M" (a sample achievement metric) and "$0.10 / MTok" (a model cost note)
# are not prices of ours.
_PRICE_LITERAL = re.compile(
    r"\$\s?[1-9]\d?(?![\d.,MKk])|(?<![\d.])[1-9]\d?\s?\$|\bUSD\b|دولار|0\.43|0\.23")


def test_no_price_is_written_anywhere_but_pricing_py():
    hits = []
    files = [*ROOT.joinpath("app", "templates").rglob("*.html"),
             *ROOT.joinpath("app").glob("*.py"),
             *ROOT.joinpath("app", "static", "js").glob("*.js"),
             *ROOT.joinpath("app", "static", "css").glob("*.css")]
    for f in files:
        if f.name in ("pricing.py", "_hero_ar_pricing.html") or "resumes" in f.parts:
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if _PRICE_LITERAL.search(line):
                hits.append(f"{f.relative_to(ROOT)}:{i}: {line.strip()[:100]}")
    assert not hits, "a price is stated outside app/pricing.py:\n  " + "\n  ".join(hits)


def test_changing_a_plan_changes_every_page(monkeypatch):
    monkeypatch.setattr(pricing, "PLANS", (
        pricing.Plan("day", 2, 1), pricing.Plan("week", 5, 7, popular=True),
        pricing.Plan("month", 9, 30)))
    c = _client(True)
    for path in ("/", "/pricing"):
        html = _get(c, path, "en").get_data(as_text=True)
        assert "$2" in html and "$5" in html and "$9" in html, path
        assert "$1<" not in html and "$7<" not in html, path
    ld = _jsonld(_get(c, "/", "en").get_data(as_text=True))
    assert [o["price"] for o in ld["@graph"][0]["offers"]] == ["2.00", "5.00", "9.00"]


def test_counts_come_from_the_registry(monkeypatch):
    monkeypatch.setattr(registry, "counts", lambda: {"modern": 13, "ats": 7, "total": 20})
    for live in (False, True):
        c = _client(live)
        en = _get(c, "/", "en").get_data(as_text=True)
        assert "13 Modern designer templates and 7 ATS templates" in en
        assert "20 designer and ATS-friendly templates" in en          # meta description
        ar = _get(c, "/", "ar").get_data(as_text=True)
        assert "13 قالباً عصرياً" in ar and "7 قوالب متوافقة" in ar
        gal = _get(c, "/templates", "en").get_data(as_text=True)
        assert "CV Templates – 20 Modern &amp; ATS Designs" in gal
        if live:
            assert "All 20 templates" in _get(c, "/pricing", "en").get_data(as_text=True)


def test_today_the_counts_are_24_and_25():
    """The user's numbers on 2026-11-16, as a tripwire, not a source."""
    assert registry.counts() == {"modern": 24, "ats": 25, "total": 49}


# ---------------------------------------------------------------- switch OFF

# "pass" alone is also a verb in the copy ("built to pass applicant tracking
# systems", "ATS CV Templates That Pass Screening"), so the noun is matched.
# "Coming soon" is not here: the builder's import button already says it.
PASS_WORDS_EN = re.compile(
    r"\b(day|week|month|a|new|your|the) pass(es)?\b|\bpasses\b|Pricing|Most popular"
    r"|auto-renewal|subscription", re.I)
PASS_WORDS_AR = re.compile(r"باقة|باقات|الأسعار|الأكثر طلباً|تجديد تلقائي|اشتراك")
FREE_PROMISES = re.compile(
    r"free|no sign-?up|no paywall|needs no account|no account needed|no account,"
    r"|مجان|بدون تسجيل|بلا تسجيل|بلا اشتراك", re.I)


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("path", PAGES)
def test_off_no_price_no_pass_no_free_promise(path, lang):
    html = _visible(_get(_client(False), path, lang).get_data(as_text=True))
    text = re.sub(r"<[^>]+>", " ", html)
    head_and_text = text + " ".join(re.findall(r'content="([^"]*)"', html))
    assert not _PRICE_LITERAL.search(head_and_text), _PRICE_LITERAL.search(head_and_text)
    words = PASS_WORDS_AR if lang == "ar" else PASS_WORDS_EN
    assert not words.search(head_and_text), words.search(head_and_text)
    assert not FREE_PROMISES.search(head_and_text), FREE_PROMISES.search(head_and_text)
    assert "/pricing" not in html and "price-buy" not in html


@pytest.mark.parametrize("lang", LANGS)
def test_off_the_pricing_page_is_a_404(lang):
    assert _get(_client(False), "/pricing", lang).status_code == 404


def test_off_no_offers_in_the_json_ld():
    for lang in LANGS:
        ld = _jsonld(_get(_client(False), "/", lang).get_data(as_text=True))
        app_node = ld["@graph"][0]
        assert "offers" not in app_node
        assert '"price"' not in json.dumps(ld)


def test_off_the_sitemap_does_not_list_pricing():
    app = create_app()
    app.config.update(TESTING=True, PAYMENTS_LIVE=False, SITE_INDEXABLE=True)
    assert "/pricing" not in app.test_client().get("/sitemap.xml").get_data(as_text=True)


# ---------------------------------------------------------------- switch ON

@pytest.mark.parametrize("lang", LANGS)
def test_on_three_cards_with_price_duration_per_day_and_inclusions(lang):
    html = _get(_client(True), "/pricing", lang).get_data(as_text=True)
    cards = re.findall(r'<article class="price-card[^"]*" data-plan="(\w+)">(.*?)</article>', html, re.S)
    assert [c[0] for c in cards] == ["day", "week", "month"]
    for (pid, body), plan in zip(cards, pricing.PLANS):
        assert pricing.fmt_usd(plan.price_usd, lang) in body
        assert pricing.fmt_usd(plan.price_per_day, lang) in body
        assert pricing.duration(plan, lang) in body
        assert ("All 49 templates" if lang == "en" else "جميع القوالب الـ49") in body
        badge = ("Most popular" if lang == "en" else "الأكثر طلباً") in body
        assert badge is plan.popular, pid


@pytest.mark.parametrize("lang", LANGS)
def test_on_the_buy_buttons_are_inert(lang):
    """No checkout exists yet, so the button is a disabled <button>, never a link."""
    html = _get(_client(True), "/pricing", lang).get_data(as_text=True)
    buttons = re.findall(r'<button class="btn btn-primary price-buy"[^>]*>(.*?)</button>', html)
    tags = re.findall(r'<button class="btn btn-primary price-buy"[^>]*>', html)
    assert len(tags) == 3 and all("disabled" in t and 'aria-disabled="true"' in t for t in tags)
    assert set(buttons) == {"Coming soon" if lang == "en" else "قريباً"}


@pytest.mark.parametrize("lang", LANGS)
def test_on_the_landing_has_the_hook_points_and_pricing(lang):
    c = _client(True)
    html = _get(c, "/", lang).get_data(as_text=True)
    assert 'id="pricing"' in html and "/pricing" in html
    if lang == "en":
        assert "Your professional CV —" in html and "starting at just $1" in html
        assert "Pay once — no subscription, no auto-renewal, no hidden fees" in html
    else:
        assert "_hero_ar_pricing" not in html  # the partial is included, not named
        assert "ابتداءً من دولار واحد فقط" in html
        assert "ادفع مرة واحدة — بلا اشتراك ولا تجديد تلقائي ولا رسوم خفية" in html
    for q in (("What does a pass unlock?", "ماذا تتيح الباقة؟"),
              ("Will I be charged again?", "هل سيُخصم المبلغ مني مرة أخرى؟")):
        assert q[0 if lang == "en" else 1] in html


def test_on_json_ld_offers_are_the_three_plans():
    ld = _jsonld(_get(_client(True), "/", "en").get_data(as_text=True))
    offers = ld["@graph"][0]["offers"]
    assert [(o["price"], o["priceCurrency"], o["eligibleDuration"]["value"]) for o in offers] == [
        ("1.00", "USD", 1), ("3.00", "USD", 7), ("7.00", "USD", 30)]


def test_on_the_sitemap_lists_pricing():
    app = create_app()
    app.config.update(TESTING=True, PAYMENTS_LIVE=True, SITE_INDEXABLE=True)
    xml = app.test_client().get("/sitemap.xml").get_data(as_text=True)
    assert "https://cvstand.com/pricing?lang=ar" in xml and "https://cvstand.com/pricing?lang=en" in xml


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("path", PAGES + ["/pricing"])
def test_on_no_free_download_or_no_sign_up_claim(path, lang):
    """Only "build and preview for free" may remain, which stays true."""
    html = _visible(_get(_client(True), path, lang).get_data(as_text=True))
    for bad in ("Free PDF", "free download", "No sign-up", "no paywall", "it's free",
                "تحميل مجاني", "بدون تسجيل", "بلا تسجيل", "مجاناً وبلا تسجيل"):
        assert bad.lower() not in html.lower(), bad


def test_both_states_shared_bullets_stay():
    for live in (False, True):
        c = _client(live)
        en = _get(c, "/", "en").get_data(as_text=True)
        ar = _get(c, "/", "ar").get_data(as_text=True)
        for s in ("Download as PDF and Word (.docx)", "Write in Arabic, English, or both",
                  "Start now", "Modern or ATS — which should I pick?"):
            assert s in en, (live, s)
        for s in ("تحميل بصيغتي PDF و Word", "اكتب سيرتك بالعربية أو الإنجليزية أو كليهما",
                  "ابدأ الآن", "مودرن أم ATS — أيّهما أختار؟"):
            assert s in ar, (live, s)


# ---------------------------------------------------------------- docs

def test_seo_copy_doc_makes_no_free_or_hard_coded_claims():
    doc = (ROOT / "docs" / "SEO_COPY.md").read_text(encoding="utf-8")
    for bad in ("Free PDF download", "تحميل مجاني", "No sign-up"):
        assert bad not in doc, bad


# ---------------------------------------------------------------- storage FAQ

def test_the_storage_answer_matches_the_deployment():
    """Deployed (SERVER_STORE=0): browser only, the account holds no copy, the
    server keeps nothing after building the file. Never "a JSON file on this
    machine", which was the local tool's answer shown to everyone."""
    from app import config
    import app as app_pkg
    for lang, needles in (("en", ("Not on our server", "your account does not keep a copy",
                                  "keeps nothing")),
                          ("ar", ("لا نحفظها على خادمنا", "لا يحتفظ حسابك بنسخة منها"))):
        a = create_app()
        a.config.update(TESTING=True)
        # the footer's own switch, injected per request (app/__init__.py)
        a.template_context_processors[None].append(lambda: {"server_store": False})
        html = _get(a.test_client(), "/", lang).get_data(as_text=True)
        for n in needles:
            assert n in html, (lang, n)
        assert "JSON file" not in html
