"""Rate limiting and render admission control.

This module exists because of one line in `app/exporters/pdf.py`:

    browser = p.chromium.launch(args=["--no-sandbox"])

Every single `/export/pdf` request launches its own Chromium process. On
127.0.0.1 with one user that is merely wasteful — a few hundred milliseconds of
startup nobody notices. On a public URL it is the whole attack: a handful of
concurrent requests is hundreds of megabytes of browser, and nothing in the app
says no. The same is true in a smaller way of `/api/photo` (Pillow decodes an
attacker-chosen image) and `/api/render` (Jinja across 49 templates).

Two different guards, because they answer two different questions:

* **Rate limit** — "is this client asking too often?" Per-client, token bucket,
  answers 429. Stops one visitor hammering an endpoint.
* **Admission control** — "is the machine already as busy as it can get?"
  Global, bounded semaphore with a bounded wait, answers 503. Stops a hundred
  polite visitors doing collectively what one rude one could not.

A rate limit alone does not save you here: fifty clients each making one PDF
request are all within any sane per-client limit, and they will still put fifty
Chromiums on the box at once. That is why `render_slot` exists separately.

In-process and in-memory on purpose. Redis would be the right answer across
several workers, and this is deliberately not that: it is the guard that makes a
single-process deployment safe, sized so the honest user never meets it. If this
ever runs multi-worker, every limit below is per worker — multiply accordingly,
and read that as the moment to move the state out, not as a reason to raise the
numbers.

Everything is tunable by environment variable so a deployment can tighten
without a code change; the defaults are chosen for one small box.
"""
from __future__ import annotations

import os
import threading
import time
from functools import wraps

from flask import jsonify, request


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, "")))
    except (TypeError, ValueError):
        return default


# How many PDF renders may be in flight at once, and how long a request will
# queue for a slot before giving up. The wait is bounded because a client
# holding a connection open for two minutes is itself a resource.
RENDER_CONCURRENCY = _env_int("CVSTAND_RENDER_CONCURRENCY", 2)
RENDER_QUEUE_WAIT = _env_int("CVSTAND_RENDER_QUEUE_WAIT", 20)

_render_slots = threading.BoundedSemaphore(RENDER_CONCURRENCY)


class RenderBusy(RuntimeError):
    """Every render slot was taken for the whole wait. Answer 503."""


class _Bucket:
    """One token bucket per client key.

    Chosen over a fixed window because a fixed window lets a client spend its
    whole allowance in the last second of one window and the whole next
    allowance in the first second of the next — double the intended burst,
    right at the boundary. A bucket refills continuously, so the burst is the
    capacity and nothing else.
    """

    __slots__ = ("tokens", "updated")

    def __init__(self, capacity: float) -> None:
        self.tokens = capacity
        self.updated = time.monotonic()


class RateLimit:
    """`capacity` requests, refilling at `per_seconds` for a full bucket."""

    def __init__(self, name: str, capacity: int, per_seconds: int) -> None:
        self.name = name
        self.capacity = float(capacity)
        self.rate = capacity / float(per_seconds)
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def _sweep(self, now: float) -> None:
        """Drop buckets that have been full and idle.

        Without this the dict is an unbounded, attacker-controlled map keyed by
        client address — a slow memory leak with a spoofable key, which is a
        poor trade for a defence against resource exhaustion. Called under the
        lock, only when the map has grown enough to be worth walking.
        """
        if len(self._buckets) < 4096:
            return
        idle = self.capacity / self.rate
        stale = [k for k, b in self._buckets.items() if now - b.updated > idle]
        for k in stale:
            del self._buckets[k]

    def check(self, key: str) -> float:
        """Spend a token for `key`. Returns 0.0 if allowed, else seconds to wait."""
        now = time.monotonic()
        with self._lock:
            self._sweep(now)
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = self._buckets[key] = _Bucket(self.capacity)
            bucket.tokens = min(
                self.capacity, bucket.tokens + (now - bucket.updated) * self.rate
            )
            bucket.updated = now
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return 0.0
            return (1.0 - bucket.tokens) / self.rate

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


def client_key() -> str:
    """Who to charge for this request.

    `request.remote_addr` behind a reverse proxy is the PROXY, which would put
    every visitor in one bucket and rate-limit the whole site as a single
    client. The fix is `ProxyFix` in the app factory, applied only when the
    deployment says it is actually behind a trusted proxy — reading
    `X-Forwarded-For` unconditionally is worse than not reading it, because
    then any client can set the header and get a fresh bucket per request.
    """
    return request.remote_addr or "unknown"


# Sized per endpoint by what the request actually costs the machine.
LIMITS = {
    # A whole Chromium each. The tightest by far.
    "pdf": RateLimit("pdf", _env_int("CVSTAND_LIMIT_PDF", 10), 60),
    # docxtpl over a Word master: cheap by comparison, still not free.
    "docx": RateLimit("docx", _env_int("CVSTAND_LIMIT_DOCX", 20), 60),
    # Pillow decoding an attacker-chosen image.
    "photo": RateLimit("photo", _env_int("CVSTAND_LIMIT_PHOTO", 20), 60),
    # Jinja only, and the builder debounces — generous so live preview never
    # trips it. A person typing cannot reach this; a script can.
    "render": RateLimit("render", _env_int("CVSTAND_LIMIT_RENDER", 120), 60),
    # The only endpoint here that costs MONEY rather than CPU. Everything else
    # in this table wastes a box you have already paid for; a call to
    # /api/assist is billed per token by a third party, so the failure mode is
    # a bill rather than a slow site. Sized for a person rewriting lines one at
    # a time and thinking in between — a human cannot reach 15/min, and the
    # daily fair-use ceiling that Phase 4 adds is a different guard for a
    # different question (this one bounds a burst, that one bounds a pass).
    "assist": RateLimit("assist", _env_int("CVSTAND_LIMIT_ASSIST", 15), 60),
    # Sign-in. Not about machine cost at all — this one bounds GUESSES.
    # scrypt makes each attempt expensive for us as well as for an attacker,
    # so the bucket protects the box and the password equally. Deliberately
    # per-CLIENT rather than per-account: locking an account by address lets
    # anyone lock anyone out, which trades a guessing problem for a denial-of-
    # service one. 10/min is far above a human retyping a password.
    "auth": RateLimit("auth", _env_int("CVSTAND_LIMIT_AUTH", 10), 60),
}


def reset_all() -> None:
    """Drop every bucket. For tests — the limiter outlives a Flask test client."""
    for limit in LIMITS.values():
        limit.reset()


def rate_limited(bucket: str):
    """429 with `Retry-After` when this client is asking too often.

    JSON rather than Flask's HTML error page, for the reason
    `routes._reject_photo` already gives: the builder shows what it is handed,
    and an HTML body forces the client back to guessing from the status code.
    """
    limit = LIMITS[bucket]

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            wait = limit.check(client_key())
            if wait:
                retry = max(1, int(wait + 0.999))
                body = jsonify({
                    "ok": False,
                    "error": "Too many requests — wait a moment and try again.",
                    "retry_after": retry,
                })
                return body, 429, {"Retry-After": str(retry)}
            return fn(*args, **kwargs)

        return wrapper

    return decorator


class render_slot:
    """Context manager holding one of the global render slots.

    Raises `RenderBusy` rather than blocking forever, so a saturated box sheds
    load instead of accumulating an unbounded queue of held connections.
    """

    def __init__(self, timeout: int = RENDER_QUEUE_WAIT) -> None:
        self.timeout = timeout
        self._held = False

    def __enter__(self) -> "render_slot":
        if not _render_slots.acquire(timeout=self.timeout):
            raise RenderBusy(
                "The export queue is full right now — try again in a moment."
            )
        self._held = True
        return self

    def __exit__(self, *exc) -> None:
        if self._held:
            _render_slots.release()
            self._held = False
