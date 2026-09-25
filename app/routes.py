"""Routes.

Pages
  GET  /                     marketing landing
  GET  /templates            gallery, category tabs (All / Modern / ATS)
  GET  /builder              the editor (stepped form + live preview)

API
  GET  /api/resume           current resume JSON + selected template
  PUT  /api/resume           replace resume JSON (validated)
  POST /api/render           {data, template_key} -> {html fragment, doc}
  GET  /preview              full standalone HTML doc for an iframe
  POST /api/template         {template_key} -> persist selection
  GET  /export/pdf           download current resume as PDF
  GET  /export/docx          download current resume as DOCX
  POST /api/assist           {job, text, target_lang} -> SSE rewrite stream

Accounts (anonymous use needs none of these)
  GET/POST /account/sign-up  create an account
  GET/POST /account/sign-in  start a session
  POST     /account/sign-out end it
  POST /api/photo            upload + square-resize a photo -> its URL
  GET  /uploads/<name>       serve an uploaded photo
"""
from __future__ import annotations

import hashlib
import io
import json

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from werkzeug.utils import secure_filename

from . import i18n as i18n_mod
from . import registry
from .config import ROOT, SERVER_STORE, UPLOADS_DIR

ROOT_STATIC = ROOT / "app" / "static"
from . import auth
from . import db
from .assist import (
    JOBS,
    AssistBadRequest,
    AssistError,
    AssistNotEntitled,
    AssistUnavailable,
    configured as assist_configured,
)
from . import brand
from .limits import RenderBusy, rate_limited, render_slot
from .labels import all_levels, levels_for, ui_catalogue, ui_t
from .exporters import DocxExportError, PdfExportError, render_docx, render_pdf
from .rendering import UnknownTemplate, canvas_html, document_html
from .schema import (
    SUPPORTED_LANGS, ResumeValidationError, typography_migrations, typography_of, validate,
)
from .store import load_meta, load_resume, load_showcase, save_resume, set_template
from .typography.ui import builder_payload as typography_payload

bp = Blueprint("main", __name__)


def _store_disabled(message: str, *, allow: str | None = None):
    """Refuse a route that only makes sense when the server holds the résumé.

    NOT `abort(405, message)`. `MethodNotAllowed`'s first positional argument is
    `valid_methods`, not `description`, so `abort(405, "some text")` spreads the
    text one character at a time into the `Allow` header. With a non-ASCII
    character in it that produced a header the real server could not send at
    all: the connection was closed with no response, which reads as "the server
    crashed" rather than "that route is off here". The Flask test client
    tolerated it and the browser suite did not — found 2026-09-10.
    """
    status = 405 if allow else 403
    headers = {"Allow": allow} if allow else {}
    return jsonify({"ok": False, "error": message}), status, headers


def _slug(data: dict) -> str:
    return secure_filename((data.get("name") or "resume").strip()) or "resume"


def _resolve_key(explicit: str | None) -> str:
    key = explicit or load_meta()["template_key"]
    tpl = registry.get(key)
    if tpl is None or not tpl.ported:
        return registry.default_key()
    return key


# ---------------------------------------------------------------- pages

@bp.get("/lang/<code>")
def set_ui_language(code: str):
    """Switch the INTERFACE language and return where the user was.

    The resume's own language is untouched: this changes what the person
    reads, not what the document is written in (app/i18n.py).

    The redirect target comes from `next`, and is accepted only if it is a
    path on this app - an absolute or scheme-relative URL from a query string
    is an open redirect, which is worth refusing even in a local single-user
    tool because the habit is what carries into a deployed one."""
    target = request.args.get("next") or url_for("main.landing")
    if not target.startswith("/") or target.startswith("//"):
        target = url_for("main.landing")
    resp = redirect(target)
    resp.set_cookie(
        i18n_mod.COOKIE, i18n_mod.normalise(code),
        max_age=i18n_mod.COOKIE_MAX_AGE, samesite="Lax", httponly=False,
    )
    return resp


@bp.get("/")
def landing():
    featured = [t for t in registry.by_category() if t.ported][:6]
    return render_template(
        "landing.html",
        categories=registry.CATEGORIES,
        featured=featured,
        counts={
            "modern": len(registry.by_category("modern")),
            "ats": len(registry.by_category("ats")),
            "live": len(registry.ported_keys()),
        },
    )


@bp.get("/templates")
def templates_gallery():
    cat = request.args.get("cat")
    if cat not in ("modern", "ats"):
        cat = None
    return render_template(
        "gallery.html",
        categories=registry.CATEGORIES,
        active_cat=cat,
        templates=registry.by_category(cat),
        meta=load_meta(),
    )


@bp.get("/builder")
def builder():
    resume = load_resume(i18n_mod.current_lang())
    # ONE LANGUAGE, chosen once, for the app AND the document.
    #
    # There used to be two: the interface followed the reader and the résumé
    # carried its own `lang`, set by a `Résumé language` control in Basics.
    # The independence was real - a bilingual applicant writing an English CV
    # from an Arabic interface - but in front of an actual user it was a
    # control that restated a choice they had already made in the header, and
    # it was removed on 2026-09-22 as useless.
    #
    # Removing it is only safe BECAUSE the document now follows the interface.
    # A control that is gone and a language that is stuck are different
    # things: someone who began an English CV and then switched the header
    # would otherwise have no way back, which is worse than the redundancy.
    #
    # What is lost, stated rather than discovered later: an Arabic interface
    # around an English résumé is no longer expressible. See
    # tests/test_document_language.py.
    doc_lang = i18n_mod.current_lang()
    # The builder generates its form in the browser, so its labels cannot go
    # through a Jinja call - the page ships the table instead. `levels` is the
    # document's vocabulary, which is now the same language as `strings`; it
    # stays a separate key because a level word is STORED in the document and
    # printed on the page, and the client has to remap the stored ones when
    # the language changes.
    return render_template(
        "builder.html",
        resume=resume,
        meta=load_meta(),
        template=registry.get(load_meta()["template_key"]),
        catalogue=[t.__dict__ for t in registry.by_category()],
        categories=registry.CATEGORIES,
        server_store=SERVER_STORE,
        i18n={
            "strings": ui_catalogue(i18n_mod.current_lang()),
            "levels": levels_for(doc_lang),
            # Both vocabularies, so the language control can re-offer the other
            # one - and translate the words already stored - without a reload.
            "levels_by_lang": all_levels(),
            "doc_lang": doc_lang,
            "doc_langs": list(SUPPORTED_LANGS),
        },
        # The Fonts section: the registry's lists for the DOCUMENT language.
        typography=typography_payload(doc_lang),
    )


# ---------------------------------------------------------------- resume CRUD

@bp.get("/api/resume")
def get_resume():
    return jsonify({"resume": load_resume(i18n_mod.current_lang()),
                    "meta": load_meta()})


@bp.put("/api/resume")
def put_resume():
    if not SERVER_STORE:
        return _store_disabled("This deployment keeps your résumé in your browser.")
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, "Body must be a JSON object.")
    try:
        validate(data)
    except ResumeValidationError as exc:
        return jsonify({"ok": False, "errors": exc.errors}), 422
    # Typography off the registry's whitelist is RESET, not refused (spec §2):
    # the stored value becomes null (template default) and `resets` tells the
    # builder what changed. Only keys the client sent are rewritten, so a
    # résumé that never chose a font is stored exactly as it was sent.
    # A résumé saved before Name/Headings were split is migrated too (its old
    # headline size moves to the name); those keys are written even though
    # the client did not send them, or the stored file would never converge.
    migrations = typography_migrations(data)
    typography, resets = typography_of(data)
    for key in typography.keys() & (data.keys() | {m["key"] for m in migrations}):
        data[key] = typography[key]
    if resets:
        current_app.logger.info("typography reset on save: %s", resets)
    save_resume(data)
    return jsonify({"ok": True, "resets": resets, "migrations": migrations})


@bp.post("/api/template")
def post_template():
    if not SERVER_STORE:
        return _store_disabled("This deployment keeps your template choice in your browser.")
    body = request.get_json(silent=True) or {}
    key = body.get("template_key")
    tpl = registry.get(key)
    if tpl is None:
        abort(400, f"Unknown template {key!r}.")
    if not tpl.ported:
        abort(409, f"{tpl.label} is not available yet.")
    set_template(key)
    return jsonify({"ok": True, "template_key": key})


# ---------------------------------------------------------------- render / preview

@bp.post("/api/render")
@rate_limited("render")
def api_render():
    body = request.get_json(silent=True) or {}
    data = body.get("data")
    if not isinstance(data, dict):
        abort(400, "`data` must be a JSON object.")
    key = _resolve_key(body.get("template_key"))
    try:
        validate(data)
    except ResumeValidationError as exc:
        return jsonify({"ok": False, "errors": exc.errors}), 422
    try:
        html = canvas_html(data, key)
        doc = document_html(data, key)
    except UnknownTemplate as exc:
        abort(400, str(exc))
    # Typography the registry does not offer for this document's language was
    # rendered as template default; say which, so the builder can clear it and
    # tell the user. Carried HERE and not only on PUT /api/resume, because a
    # deployment never sends that PUT (the browser is the store), while every
    # preview comes through this route.
    # `migrations` carry a pre-split résumé onto the Name/Headings model; the
    # builder applies them silently to its stored copy (nothing visible moves).
    _, resets = typography_of(data)
    return jsonify({"ok": True, "html": html, "doc": doc, "template_key": key,
                    "resets": resets, "migrations": typography_migrations(data)})


@bp.get("/preview")
def preview():
    """One route, two jobs, told apart by `showcase`.

    WITHOUT it — the builder's live preview and the template drawer: renders
    the user's OWN résumé, because there you are choosing a layout for your
    own content and stock text would be a lie.

    WITH it — the landing hero and the gallery cards: renders the showcase
    sample for the READER's interface language. Those surfaces demonstrate
    what a layout looks like, so an Arabic visitor sees Arabic résumés and an
    English visitor sees English ones, whatever language the document in
    `data/resume.json` happens to be written in.

    Note the two languages stay independent (app/i18n.py): this reads the
    `ui_lang` cookie, never `resume["lang"]`, and it never writes anything.
    """
    key = _resolve_key(request.args.get("template_key"))
    if request.args.get("showcase"):
        data = load_showcase(i18n_mod.current_lang())
    else:
        data = load_resume(i18n_mod.current_lang())
    return Response(document_html(data, key), mimetype="text/html")


# ---------------------------------------------------------------- exports

class _ExportNeedsPost(Exception):
    """GET is off in this deployment — the résumé must come in the body."""


class _BadExportBody(ValueError):
    """The posted résumé is not renderable. Carries the schema's own errors."""

    def __init__(self, errors):
        self.errors = errors


def _export_subject():
    """The résumé to export, and the template to export it in.

    Two methods on purpose, and the difference is the whole deployment story:

    **POST** — the client sends the résumé in the body. This is what the
    builder uses, and it is the only shape that works for more than one person
    at a time: the document lives in the visitor's own browser and the server
    never stores it. No account needed to be safe, because there is nothing
    server-side to mix up between two visitors.

    **GET** — the server exports whatever is in `data/resume.json`. That file
    is a SINGLE global résumé, so on a public URL two visitors would export
    each other's document. It stays because the local single-user workflow and
    the browser suite are both built on it, and because `curl localhost/export/pdf`
    is genuinely useful on your own machine — but it must be off in a
    multi-visitor deployment. `CVSTAND_SERVER_STORE=0` is that switch.
    """
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        data = body.get("data")
        if not isinstance(data, dict):
            raise _BadExportBody([{"path": "data", "message": "must be a JSON object"}])
        try:
            validate(data)
        except ResumeValidationError as exc:
            raise _BadExportBody(exc.errors) from exc
        return data, _resolve_key(body.get("template_key"))

    if not SERVER_STORE:
        raise _ExportNeedsPost()
    return (load_resume(i18n_mod.current_lang()),
            _resolve_key(request.args.get("template_key")))


@bp.route("/export/pdf", methods=["GET", "POST"])
@rate_limited("pdf")
def export_pdf():
    try:
        data, key = _export_subject()
    except _ExportNeedsPost:
        return _store_disabled(
            "This deployment exports the résumé you send it — use POST.",
            allow="POST",
        )
    except _BadExportBody as exc:
        return jsonify({"ok": False, "errors": exc.errors}), 422
    try:
        # One Chromium per request (app/exporters/pdf.py). The slot is what
        # keeps a burst of exports from putting N of them on the box at once;
        # the rate limit above only governs how often ONE client may ask.
        with render_slot():
            pdf = render_pdf(data, key)
    except RenderBusy as exc:
        current_app.logger.warning("PDF export shed: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 503, {"Retry-After": "30"}
    except PdfExportError as exc:
        current_app.logger.exception("PDF export failed")
        abort(500, str(exc))
    return send_file(
        io.BytesIO(pdf),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{_slug(data)}.pdf",
    )


@bp.route("/export/docx", methods=["GET", "POST"])
@rate_limited("docx")
def export_docx():
    try:
        data, key = _export_subject()
    except _ExportNeedsPost:
        return _store_disabled(
            "This deployment exports the résumé you send it — use POST.",
            allow="POST",
        )
    except _BadExportBody as exc:
        return jsonify({"ok": False, "errors": exc.errors}), 422
    try:
        blob = render_docx(data, key)
    except DocxExportError as exc:
        current_app.logger.warning("DOCX export unavailable: %s", exc)
        abort(501, str(exc))
    return send_file(
        io.BytesIO(blob),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=f"{_slug(data)}.docx",
    )


# ---------------------------------------------------------------- PWA

@bp.get("/manifest.webmanifest")
def manifest():
    """The install manifest, in the READER's interface language.

    Rendered rather than served as a static file because the shell is
    bilingual: `name`, `description`, `lang` and `dir` all differ between an
    Arabic and an English visitor, and a static manifest would name the
    installed app in whichever language happened to be written into the file.
    The `ui_lang` cookie decides, exactly as it does for every other shell
    string (app/i18n.py) — and never `resume["lang"]`, which is the document's
    own language and a different question.
    """
    lang = i18n_mod.current_lang()
    return jsonify({
        # The brand, NOT run through ui_t(): a brand does not change script
        # when the interface does, so the wrapper was always a no-op here.
        "name": brand.NAME,
        "short_name": brand.NAME,
        "description": ui_t(
            "Build a résumé in minutes — 49 designer layouts, PDF and Word.", lang),
        "lang": lang,
        "dir": "rtl" if lang == "ar" else "ltr",
        "start_url": "/builder",
        "scope": "/",
        "display": "standalone",
        "background_color": "#fbfbfd",
        "theme_color": "#4f46e5",
        "icons": [
            {"src": url_for("static", filename="icons/icon-192.png"),
             "sizes": "192x192", "type": "image/png"},
            {"src": url_for("static", filename="icons/icon-512.png"),
             "sizes": "512x512", "type": "image/png"},
            {"src": url_for("static", filename="icons/icon-maskable-512.png"),
             "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    })


@bp.get("/sw.js")
def service_worker():
    """The worker, served from the ROOT so its scope is the whole app.

    A worker registered from /static/js/sw.js may only control /static/ — it
    would cache the stylesheet and never see a single page. The file lives
    under static/ for editing; this route is what gives it authority.
    """
    resp = send_file(ROOT_STATIC / "js" / "sw.js", mimetype="text/javascript")
    # Belt and braces: the scope is already / because the script is served
    # from /, but this makes the intent explicit and survives a move.
    resp.headers["Service-Worker-Allowed"] = "/"
    # A stale worker is a stale APP — it decides what every other response is
    # allowed to be. Never let an intermediary hold on to it.
    resp.headers["Cache-Control"] = "no-cache"
    return resp


# ---------------------------------------------------------------- photo upload

_ALLOWED_IMG = {"image/png", "image/jpeg", "image/webp"}

_NOT_AN_IMAGE = "That file is not a photo — use a PNG, JPEG or WebP."
_BROKEN_IMAGE = "That photo is damaged or incomplete — try another file."


def _reject_photo(msg: str, code: int = 415):
    """Answer a bad upload in JSON rather than Flask's HTML error page.

    The builder shows `error` verbatim. An HTML body would force it back to
    guessing the reason from the status code, which is how the wrong layer got
    named the last time this path failed.
    """
    return jsonify({"ok": False, "error": msg}), code


@bp.post("/api/photo")
@rate_limited("photo")
def upload_photo():
    file = request.files.get("photo")
    if file is None or not file.filename:
        return _reject_photo("No file was chosen.", 400)
    if file.mimetype not in _ALLOWED_IMG:
        return _reject_photo(_NOT_AN_IMAGE)
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError:  # pragma: no cover
        abort(500, "Pillow is not installed.")

    # THE MIMETYPE ABOVE IS THE BROWSER'S GUESS FROM THE FILE EXTENSION, NOT
    # FROM THE BYTES. Renaming notes.txt to notes.png makes the browser send
    # `image/png`, so that gate only catches a user who picked a file with an
    # honest extension. Two shapes get through it, both ordinary:
    #   * a non-image with an image extension -> UnidentifiedImageError here
    #   * a truncated photo (interrupted download, failing card) -> a valid
    #     header, so `open()` succeeds and it fails later, inside crop()
    # Both used to escape as an unhandled 500, which the builder reported as
    # "error 500" — blaming the server for the user's file. `load()` forces the
    # decode now, so the failure happens where it can still be explained.
    try:
        img = Image.open(file.stream)
        img.load()
    except UnidentifiedImageError:
        return _reject_photo(_NOT_AN_IMAGE)
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        current_app.logger.info("rejected photo %r: %s", file.filename, exc)
        return _reject_photo(_BROKEN_IMAGE)

    side = min(img.size)
    left = (img.width - side) // 2
    top = (img.height - side) // 2
    img = img.crop((left, top, left + side, top + side)).convert("RGB")
    img.thumbnail((512, 512), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    digest = hashlib.sha1(buf.getvalue()).hexdigest()[:16]
    name = f"{digest}.jpg"
    (UPLOADS_DIR / name).write_bytes(buf.getvalue())
    return jsonify({"ok": True, "url": url_for("main.photo", name=name)})


@bp.get("/uploads/<name>")
def photo(name: str):
    name = secure_filename(name)
    path = UPLOADS_DIR / name
    if not path.exists():
        abort(404)
    return send_file(path)


# ------------------------------------------------------------------- assistant

def _assist_error(message: str, code: int):
    """JSON, for the reason `_reject_photo` already gives.

    The builder shows what it is handed; an HTML error page forces the client
    back to guessing from the status code, and this project's whole history of
    silent failures is error messages that name the wrong layer.
    """
    return jsonify({"ok": False, "error": message}), code


@bp.post("/api/assist")
@rate_limited("assist")
def api_assist():
    """Stream one AI rewrite back as server-sent events.

    Nothing here writes to a résumé, by design: the assistant PROPOSES, the
    user accepts, and the accepted value goes through `validate()` on the
    ordinary path like anything else they typed. See `app/assist.py` for why
    that boundary is the whole defence.

    The first chunk is pulled BEFORE the response is constructed. Everything
    `adapt()` refuses — no entitlement, no key, empty or oversized text, an
    unsupported language — raises on the first `next()`, and a generator is
    lazy, so handing Flask the raw generator would send `200 text/event-stream`
    and only then discover the request was a 402. Pulling one chunk first means
    a refusal is still an HTTP status the client can branch on, and a failure
    mid-stream (the only kind left) is reported as an `error` frame inside a
    stream that has honestly already begun.
    """
    body = request.get_json(silent=True) or {}
    job = body.get("job") or "adapt"
    if job not in JOBS:
        return _assist_error(f"`{job}` is not something the assistant does.", 400)
    if not assist_configured():
        return _assist_error(
            "AI writing help is not switched on for this server.", 503
        )

    context = body.get("context")
    try:
        stream = JOBS[job](
            body.get("text") or "",
            target_lang=body.get("target_lang") or "",
            context=context if isinstance(context, dict) else None,
        )
        first = next(stream)
    except AssistNotEntitled as exc:
        return _assist_error(str(exc), 402)
    except AssistUnavailable as exc:
        return _assist_error(str(exc), 503)
    except AssistBadRequest as exc:
        return _assist_error(str(exc), 400)
    except AssistError as exc:
        return _assist_error(str(exc), 502)
    except StopIteration:
        return _assist_error("The assistant returned nothing.", 502)

    def frames():
        yield f"data: {json.dumps(first, ensure_ascii=False)}\n\n"
        try:
            for chunk in stream:
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        except AssistError as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)}, ensure_ascii=False)}\n\n"
        except Exception:
            # The provider or the network failed mid-answer. Say which layer
            # broke rather than letting the client infer it from a truncated
            # stream, and do NOT echo the exception — it can carry the request.
            yield (
                'data: {"type": "error", "error": '
                '"The writing service stopped responding."}\n\n'
            )

    return Response(
        frames(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------- accounts

def _safe_next(raw: str | None) -> str:
    """A redirect target, accepted only if it is a path on this app.

    Same rule as `set_ui_language`, and worth repeating rather than trusting:
    an absolute or scheme-relative URL arriving in a form field or query string
    is an open redirect, and an open redirect on a SIGN-IN page is the classic
    credential-phishing setup — the user checks the domain, signs in for real,
    and is then bounced to a lookalike that asks again.
    """
    if not raw or not raw.startswith("/") or raw.startswith("//"):
        return url_for("main.builder")
    return raw


def _account_page(mode: str, *, error: str = "", email: str = "", status: int = 200):
    """Render the account form.

    `error` is an ENGLISH MSGID, not a translated string, and the template
    runs it through `t()`. The first cut called `ui_t()` here instead — whose
    signature is `ui_t(text, lang="en")` — so with no language argument every
    heading, button and error rendered in English on the Arabic page while the
    rest of it mirrored correctly. `test_labels.py` passed throughout, because
    the catalogue rows existed; nothing was reading them.
    """
    body = render_template(
        "account.html",
        mode=mode,
        error=error,
        email=email,
        next_url=_safe_next(request.values.get("next")),
        min_password=auth.MIN_PASSWORD_LENGTH,
    )
    return (body, status) if status != 200 else body


@bp.route("/account/sign-up", methods=["GET", "POST"])
@rate_limited("auth")
def sign_up_page():
    if auth.current_user() is not None:
        return redirect(_safe_next(request.values.get("next")))
    if request.method == "GET":
        return _account_page("signup")

    email = request.form.get("email", "")
    try:
        user_id = auth.create_user(email, request.form.get("password", ""))
    except auth.AuthError as exc:
        # 400, not 200: the request was not accepted, and a status that says
        # otherwise makes the failure invisible to anything but a human eye.
        return _account_page("signup", error=str(exc), email=email, status=400)

    auth.sign_in(db.query_one("SELECT * FROM users WHERE id = ?", (user_id,)))
    return redirect(_safe_next(request.form.get("next")))


@bp.route("/account/sign-in", methods=["GET", "POST"])
@rate_limited("auth")
def sign_in_page():
    if auth.current_user() is not None:
        return redirect(_safe_next(request.values.get("next")))
    if request.method == "GET":
        return _account_page("signin")

    email = request.form.get("email", "")
    row = auth.authenticate(email, request.form.get("password", ""))
    if row is None:
        # One message for "no such account" and for "wrong password". Telling
        # them apart hands an unauthenticated stranger a way to enumerate who
        # has an account here. `auth.authenticate` also equalises the TIMING,
        # since a fast "no such user" leaks the same thing more quietly.
        return _account_page(
            "signin", error="That email and password do not match.",
            email=email, status=401,
        )
    auth.sign_in(row)
    return redirect(_safe_next(request.form.get("next")))


@bp.post("/account/sign-out")
def sign_out_page():
    """POST only, and that is not pedantry.

    A GET that changes state is CSRF-able from any page with an <img> tag, and
    browsers and link-prefetchers fetch GET links speculatively — a sign-out
    link would log people out while they were still reading.
    """
    auth.sign_out()
    return redirect(url_for("main.landing"))
