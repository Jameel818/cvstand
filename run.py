"""Dev entrypoint: `python run.py` -> http://127.0.0.1:5000

By default the local app behaves like the LIVE site: the browser owns the
résumé (CVSTAND_SERVER_STORE=0), so a fresh visitor starts from the demo CV in
the interface language - Arabic gets the Arabic demo, right to left - and every
export is the document on screen. Before this, the local app read the single
global data/resume.json (whatever was last typed into it, in whatever
language), so the local builder showed neither the Arabic sample nor the
templates' Word designs the way a real visitor sees them (run 4, items 1-2).

    python run.py                  live-like (browser store)
    python run.py --server-store   the old single-user mode: data/resume.json

Production does not use this file (Dockerfile: gunicorn "app:create_app()").
"""
import os
import secrets
import sys

if "--server-store" in sys.argv:
    os.environ.setdefault("CVSTAND_SERVER_STORE", "1")
else:
    os.environ.setdefault("CVSTAND_SERVER_STORE", "0")
    # multi-visitor mode refuses the built-in key (app/__init__.py): a throwaway
    # one for this local process only - sessions simply reset on restart
    os.environ.setdefault("SECRET_KEY", secrets.token_urlsafe(48))

from app import create_app  # noqa: E402  (the flags above are read at import)

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
