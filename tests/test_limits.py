"""The guards that make a public deployment survivable.

`app/limits.py` exists for one line in `app/exporters/pdf.py` — a fresh
Chromium per `/export/pdf` request. These tests hold both guards to their
contracts, and the distinction between them is the point:

* the RATE LIMIT is per client and answers 429 — one visitor asking too often;
* ADMISSION CONTROL is global and answers 503 — the machine already as busy as
  it is willing to get, however many polite clients caused it.

The second is the one a rate limit cannot do. Fifty clients making one PDF
request each are all inside any per-client limit, and would still put fifty
browsers on the box at once. `test_admission_sheds_when_all_slots_are_taken`
is the test that would fail if someone "simplified" the semaphore away on the
grounds that there is already a rate limiter.

No test here sleeps to wait out a bucket. Sleeping for real time makes a suite
slow and flaky in exactly proportion to how thoroughly it tests; the refill
maths is checked directly against a `RateLimit` instead.
"""
from __future__ import annotations

import threading
import time

import pytest

from app import create_app
from app.limits import LIMITS, RateLimit, RenderBusy, render_slot


@pytest.fixture
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------- the bucket

def test_capacity_is_the_burst():
    limit = RateLimit("t", capacity=3, per_seconds=60)
    assert [limit.check("a") for _ in range(3)] == [0.0, 0.0, 0.0]
    assert limit.check("a") > 0.0


def test_clients_are_charged_separately():
    """One noisy client must not spend anybody else's allowance."""
    limit = RateLimit("t", capacity=2, per_seconds=60)
    limit.check("a"), limit.check("a")
    assert limit.check("a") > 0.0
    assert limit.check("b") == 0.0, "b was charged for a's requests"


def test_refill_is_continuous_not_a_window():
    """A fixed window allows double the burst across its boundary.

    Spend the whole allowance, then move time to the boundary: a fixed-window
    limiter would hand back the FULL allowance at once. A bucket hands back
    exactly what elapsed.
    """
    limit = RateLimit("t", capacity=10, per_seconds=10)  # 1 token/sec
    for _ in range(10):
        limit.check("a")
    bucket = limit._buckets["a"]
    bucket.updated -= 3.0  # pretend three seconds passed
    assert [limit.check("a") for _ in range(3)] == [0.0, 0.0, 0.0]
    assert limit.check("a") > 0.0, "refilled more than the elapsed time earned"


def test_retry_after_is_a_real_wait():
    limit = RateLimit("t", capacity=1, per_seconds=60)
    limit.check("a")
    wait = limit.check("a")
    assert 0 < wait <= 60


def test_buckets_do_not_grow_without_bound():
    """The map is keyed by a client-controlled value, so it must be swept.

    Otherwise the defence against resource exhaustion is itself a slow,
    attacker-driven memory leak.
    """
    limit = RateLimit("t", capacity=1, per_seconds=1)
    for i in range(5000):
        limit.check(f"client-{i}")
    for bucket in limit._buckets.values():
        bucket.updated -= 3600
    limit.check("trigger-the-sweep")
    assert len(limit._buckets) < 5000, "idle buckets were never reclaimed"


# ---------------------------------------------------------------- the routes

def test_render_answers_429_when_asked_too_often(client):
    limit = LIMITS["render"]
    payload = {"data": {"name": "X"}, "template_key": "modern-t1"}
    seen = None
    for _ in range(int(limit.capacity) + 2):
        res = client.post("/api/render", json=payload)
        if res.status_code == 429:
            seen = res
            break
    assert seen is not None, "the render limit never engaged"
    assert seen.headers.get("Retry-After"), "429 without Retry-After"
    body = seen.get_json()
    assert body["ok"] is False
    assert body["retry_after"] >= 1


def test_limit_response_is_json_not_an_html_error_page(client):
    """The builder shows what it is handed; an HTML body forces it back to
    guessing the reason from the status code. Same rule as `_reject_photo`."""
    limit = LIMITS["photo"]
    res = None
    for _ in range(int(limit.capacity) + 2):
        res = client.post("/api/photo", data={})
        if res.status_code == 429:
            break
    assert res.status_code == 429
    assert res.is_json, "rate-limit response was not JSON"
    assert "error" in res.get_json()


def test_ordinary_use_never_trips_a_limit(client):
    """A guard that fires on normal use is a bug, not a defence."""
    payload = {"data": {"name": "X"}, "template_key": "modern-t1"}
    for _ in range(20):
        assert client.post("/api/render", json=payload).status_code != 429


# ---------------------------------------------------------------- admission

def test_admission_sheds_when_all_slots_are_taken():
    """503 rather than an unbounded queue of held connections."""
    held = []
    try:
        while True:
            slot = render_slot(timeout=0)
            try:
                slot.__enter__()
            except RenderBusy:
                break
            held.append(slot)
            assert len(held) < 64, "the semaphore appears to be unbounded"
        with pytest.raises(RenderBusy):
            with render_slot(timeout=0):
                pass
    finally:
        for slot in held:
            slot.__exit__(None, None, None)


def test_a_released_slot_is_reusable():
    with render_slot(timeout=1):
        pass
    with render_slot(timeout=1):
        pass


def test_a_raising_render_still_gives_its_slot_back():
    """A failed export must not permanently consume capacity.

    This is the leak that turns one bad résumé into a dead endpoint: if the
    slot is not released on the error path, every failure shrinks the pool
    until nothing can export at all.
    """
    with pytest.raises(ValueError):
        with render_slot(timeout=1):
            raise ValueError("boom")
    with render_slot(timeout=1):
        pass


def test_waiting_is_bounded():
    """A full pool makes the caller wait, then gives up — it does not hang."""
    blocker = render_slot(timeout=1)
    blockers = [blocker]
    blocker.__enter__()
    try:
        while True:
            extra = render_slot(timeout=0)
            try:
                extra.__enter__()
            except RenderBusy:
                break
            blockers.append(extra)
        started = time.monotonic()
        with pytest.raises(RenderBusy):
            with render_slot(timeout=1):
                pass
        waited = time.monotonic() - started
        assert 0.5 < waited < 5, f"waited {waited:.2f}s, expected ~1s"
    finally:
        for slot in blockers:
            slot.__exit__(None, None, None)


def test_slots_are_actually_exclusive():
    """Two threads must not both be inside the pool beyond its size."""
    inside = []
    peak = []
    lock = threading.Lock()

    def worker():
        try:
            with render_slot(timeout=2):
                with lock:
                    inside.append(1)
                    peak.append(len(inside))
                time.sleep(0.05)
                with lock:
                    inside.pop()
        except RenderBusy:
            pass

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    from app.limits import RENDER_CONCURRENCY

    assert max(peak) <= RENDER_CONCURRENCY, (
        f"{max(peak)} renders ran at once, cap is {RENDER_CONCURRENCY}"
    )
