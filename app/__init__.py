"""Flask app factory. Single-user resume builder, v1."""
from __future__ import annotations

import mimetypes
import os

from flask import Flask

from . import brand
from .config import Config, DATA_DIR, DEFAULT_SECRET_KEY, SERVER_STORE, UPLOADS_DIR


class InsecureDeployment(RuntimeError):
    """Refuse to start rather than serve forgeable sessions."""


def create_app(config_object: type = Config) -> Flask:
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_object)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    # Flask signs the session cookie with SECRET_KEY. Before accounts existed
    # that cookie carried nothing worth forging and the built-in default was
    # harmless. It now carries WHO YOU ARE, so a known key is not a weak
    # password — it is the ability to mint a session as any user, including
    # one holding a paid pass, without touching the database.
    #
    # `SERVER_STORE` is already the documented "this is a real deployment"
    # switch (app/config.py), so it is the honest signal to gate on: local
    # single-user work keeps working untouched, and a deployment refuses to
    # boot with the shipped default rather than running quietly insecure.
    # Failing at startup is the point — a warning in a log nobody reads is how
    # this ships anyway.
    if not SERVER_STORE and app.config["SECRET_KEY"] == DEFAULT_SECRET_KEY:
        raise InsecureDeployment(
            "SECRET_KEY is still the built-in default, and this deployment has "
            "CVSTAND_SERVER_STORE=0 (multi-visitor). Session cookies carry "
            "the signed-in user, so a known key lets anyone forge an account. "
            "Set SECRET_KEY to a long random value, e.g. "
            "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )

    # Windows has no registry entry for .woff2, so Flask would serve the
    # self-hosted fonts as application/octet-stream.
    mimetypes.add_type("font/woff2", ".woff2")

    # Behind a reverse proxy, `request.remote_addr` is the PROXY. Every visitor
    # would then share one rate-limit bucket and the whole site would throttle
    # as a single client. ProxyFix makes Werkzeug read X-Forwarded-For instead.
    #
    # Opt-in, and that is the security-relevant half: X-Forwarded-For is a
    # request HEADER, so if it is trusted when nothing is actually stripping it,
    # any client can set it and mint itself a fresh bucket per request —
    # strictly worse than not reading it at all. `CVSTAND_TRUSTED_PROXIES`
    # is the count of proxies in front of this app (1 for a single nginx or
    # load balancer); leave it unset for a direct-to-Flask deployment.
    proxies = int(os.environ.get("CVSTAND_TRUSTED_PROXIES") or 0)
    if proxies > 0:
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=proxies, x_proto=proxies, x_host=proxies
        )

    from . import db as _db
    from . import i18n
    from .routes import bp

    # Accounts, sessions and (Phase 2) entitlement. Creating the schema at
    # startup rather than lazily means a broken data directory is a boot
    # failure, not a 500 on somebody's first sign-in.
    _db.register(app)
    _db.init()

    # Interface language (cookie-driven) for the app shell. Independent of
    # the resume's own `lang` - see app/i18n.py for why.
    i18n.register(app)
    app.register_blueprint(bp)

    # The public brand, on every page. A context processor rather than a
    # per-route variable for the same reason as `_current_user` below:
    # base.html renders on EVERY page, and a route that forgot to pass it
    # would render an empty wordmark. Defined once in app/brand.py -- see
    # that file for why the constant exists at all.
    @app.context_processor
    def _brand():
        return brand.context()

    # Every page's footer says where the résumé lives, and the true answer
    # differs between the local tool and a deployment. See app/config.py.
    @app.context_processor
    def _store_mode():
        return {"server_store": SERVER_STORE}

    # Every page's header can show who is signed in. A context processor
    # rather than a per-route variable, because base.html renders on EVERY
    # page and a route that forgot to pass it would silently show a signed-in
    # person as anonymous.
    @app.context_processor
    def _current_user():
        from .auth import current_user

        return {"current_user": current_user()}

    return app
