"""Interface language for the app shell (phase 6).

Two languages live in this app and they are deliberately independent:

  the DOCUMENT language   `resume["lang"]`   what the resume is written in
  the INTERFACE language  the `ui_lang` cookie   what the person reading the
                                                 app prefers

Editing an English resume from an Arabic interface is an ordinary case - a
bilingual user applying to an English-speaking employer - so tying the two
together would be wrong. That independence was one of the four assumptions
recorded when the bilingual plan was written, and it is the reason the shell
has its own resolver rather than reading `resume["lang"]`.

The cookie is the whole mechanism: no session, no account, no server state, in
an app whose selling point is that it runs locally and stores nothing.

Anything not in the catalogue renders in English rather than raising, the same
degrade rule the document labels follow: a missing translation must not 500 the
interface. Coverage is a test failure instead.
"""
from __future__ import annotations

from flask import request

from .labels import ui_catalogue, ui_t

#: Interface languages. An unknown cookie value falls back to English rather
#: than being trusted - the cookie is user-editable input like any other.
UI_LANGS = ("en", "ar")
DEFAULT_UI_LANG = "en"
COOKIE = "ui_lang"
#: A year. The choice is a preference, not a session.
COOKIE_MAX_AGE = 60 * 60 * 24 * 365

_RTL = {"ar"}


def normalise(lang: str | None) -> str:
    return lang if lang in UI_LANGS else DEFAULT_UI_LANG


def current_lang() -> str:
    """The interface language for this request."""
    return normalise(request.cookies.get(COOKIE))


def dir_for(lang: str) -> str:
    return "rtl" if lang in _RTL else "ltr"


def register(app) -> None:
    """Expose `t()`, `ui_lang` and `ui_dir` to every shell template.

    A context processor rather than a Jinja global, because the value depends
    on the REQUEST: a global is evaluated once per environment and would pin
    the whole app to whichever language happened to be asked for first.
    """

    @app.context_processor
    def _inject():
        lang = current_lang()
        return {
            "t": lambda s: ui_t(s, lang),
            "ui_lang": lang,
            "ui_dir": dir_for(lang),
            "ui_langs": UI_LANGS,
            "ui_catalogue": lambda: ui_catalogue(lang),
        }
