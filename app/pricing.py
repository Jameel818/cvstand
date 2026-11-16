"""THE one source of truth for what CVStand charges, and the switch that hides it.

Every price, duration and per-day figure the site shows is computed here: the
landing hero, the pricing cards, the FAQ, the meta descriptions and the JSON-LD
offers. A template or a catalogue row never contains a price. It contains a
`{price}` placeholder that `fill()` replaces with a value from this module.
`tests/test_pricing.py` greps the tree to keep it that way.

PAYMENTS_LIVE (app/config.py, env CVSTAND_PAYMENTS_LIVE, default 0)
    Read only through `payments_live()`, from the app config at request time,
    so a test can flip it on one app.
    0: no price, no pass wording, no pricing nav link, /pricing is a 404, no
       pass items in the FAQ, no offers in the JSON-LD, and no
       "free download" / "no sign-up" promise either: the copy is neutral.
    1: the full pricing copy. The buy buttons are still inert, because no
       gateway exists yet.
    Nothing here gates a download. Payment is not built.

ARABIC NUMBERS
    A counted noun in Arabic changes form with the number, and so does its
    adjective: 7 أيام, 30 يوماً, 24 قالباً عصرياً. `ar_count` does that. So a
    count from the registry can change and the sentence stays grammatical.
"""
from __future__ import annotations

from dataclasses import dataclass

from flask import current_app
from markupsafe import Markup

from . import registry

CURRENCY = "USD"
AUTO_RENEW = False


@dataclass(frozen=True)
class Plan:
    id: str
    price_usd: float
    days: int
    popular: bool = False

    @property
    def price_per_day(self) -> float:
        return self.price_usd / self.days


PLANS: tuple[Plan, ...] = (
    Plan("day", 1, 1),
    Plan("week", 3, 7, popular=True),
    Plan("month", 7, 30),
)


def lowest() -> Plan:
    return min(PLANS, key=lambda p: p.price_usd)


def payments_live() -> bool:
    return bool(current_app.config.get("PAYMENTS_LIVE"))


# ---------------------------------------------------------------- formatting

def fmt_usd(amount: float, lang: str = "en") -> str:
    """"$1" / "$0.43"; Arabic puts the sign after: "1$" / "0.43$".

    Callers wrap it in <bdi dir="ltr"> so the bidi algorithm cannot move the sign.
    """
    cents = round(amount * 100)
    num = f"{cents // 100}" if cents % 100 == 0 else f"{cents / 100:.2f}"
    return f"{num}$" if lang == "ar" else f"${num}"


#: Arabic forms of a counted noun phrase:
#: (one, two, 3-10 plural, 11-99 accusative singular, 100-style singular).
#: "one" and "two" are complete phrases with no digit, as Arabic writes them.
AR_TEMPLATE = ("قالب واحد", "قالبان", "قوالب", "قالباً", "قالب")
AR_MODERN = ("قالب عصري واحد", "قالبان عصريان", "قوالب عصرية", "قالباً عصرياً", "قالب عصري")
AR_ATS = ("قالب واحد متوافق", "قالبان متوافقان", "قوالب متوافقة", "قالباً متوافقاً", "قالب متوافق")
AR_DAY = ("يوم واحد", "يومان", "أيام", "يوماً", "يوم")
AR_HOUR = ("ساعة واحدة", "ساعتان", "ساعات", "ساعة", "ساعة")
AR_DOLLAR = ("دولار واحد", "دولاران", "دولارات", "دولاراً", "دولار")


def ar_count(n: int, forms: tuple[str, str, str, str, str]) -> str:
    """The number and its counted noun, with Arabic agreement.

    The last two digits decide the form: 3-10 take the plural, 11-99 the
    accusative singular, and 0, 1 or 2 (100, 101, 102 ...) the singular.
    Only 1 and 2 on their own are written as words.
    """
    one, two, few, many, single = forms
    if n == 1:
        return one
    if n == 2:
        return two
    r = n % 100
    if 3 <= r <= 10:
        return f"{n} {few}"
    if 11 <= r <= 99:
        return f"{n} {many}"
    return f"{n} {single}"


def duration(plan: Plan, lang: str) -> str:
    """'24 hours' for the one-day pass, else 'N days'."""
    if plan.days == 1:
        return ar_count(24, AR_HOUR) if lang == "ar" else "24 hours"
    return ar_count(plan.days, AR_DAY) if lang == "ar" else f"{plan.days} days"


# ---------------------------------------------------------------- copy values

def copy_values(lang: str) -> dict[str, str]:
    """Every value a `{placeholder}` in the copy can name, for one language.

    Pure: no request needed, so tools/outline_text.py can build the Arabic
    hero from the same numbers the page shows.
    """
    c = registry.counts()
    low = lowest()
    return {
        "modern": str(c["modern"]),
        "ats": str(c["ats"]),
        "total": str(c["total"]),
        "modern_ar": ar_count(c["modern"], AR_MODERN),
        "ats_ar": ar_count(c["ats"], AR_ATS),
        "total_ar": ar_count(c["total"], AR_TEMPLATE),
        "price": fmt_usd(low.price_usd, lang),
        "price_words": ar_count(int(low.price_usd), AR_DOLLAR)
        if float(low.price_usd).is_integer() else fmt_usd(low.price_usd, lang),
    }


def fill(text, values: dict[str, str]):
    """Replace each `{name}` in already-translated copy.

    It runs after `t()`, so one placeholder serves both languages. It uses
    str.replace rather than str.format, because copy may contain other braces.
    On Markup, `.replace` escapes the inserted value, which is what we want.
    """
    for k, v in values.items():
        text = text.replace("{" + k + "}", v)
    return text


def offers() -> list[dict]:
    """schema.org Offers for the JSON-LD. Only called while payments are live."""
    return [
        {
            "@type": "Offer",
            "name": f"{p.id.capitalize()} pass",
            "price": f"{p.price_usd:.2f}",
            "priceCurrency": CURRENCY,
            "eligibleDuration": {"@type": "QuantitativeValue",
                                 "value": p.days, "unitCode": "DAY"},
        }
        for p in PLANS
    ]


def register(app) -> None:
    from .i18n import current_lang

    app.add_template_filter(fill, "fill")

    @app.context_processor
    def _pricing():
        from flask import has_request_context
        if not has_request_context():
            return {}
        lang = current_lang()
        return {
            "payments_live": payments_live(),
            "plans": PLANS,
            "copy_vals": copy_values(lang),
            "plan_price": lambda p: fmt_usd(p.price_usd, lang),
            # Markup with <bdi>: it is filled into a sentence, and the
            # currency sign must not be moved by the surrounding direction.
            "plan_per_day": lambda p: Markup('<bdi dir="ltr">%s</bdi>')
            % fmt_usd(p.price_per_day, lang),
            "plan_duration": lambda p: duration(p, lang),
        }
