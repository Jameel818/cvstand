"""`POST /api/photo` — what happens to a file that is not a usable image.

DEFECT 6 (2026-09-06). The handler gated on `file.mimetype`, which is the
**browser's guess from the file extension**, not a reading of the bytes. So the
gate only ever caught a user who picked a file with an honest extension. Two
perfectly ordinary shapes walked through it and hit Pillow unguarded:

  * a non-image carrying an image extension — `notes.txt` renamed `shot.png`
    makes a real browser send `image/png` — raised `UnidentifiedImageError`;
  * a truncated photo (interrupted download, failing SD card) — the header is
    intact so `Image.open()` *succeeds*, and it blew up later inside `crop()`
    with "image file is truncated".

Both escaped as an unhandled **500**, which the builder printed as "error 500":
the app blaming its own server for the user's file. That is this project's
recurring failure shape — an error message naming the wrong layer — so the
reason now comes from the server, which is the only party that read the bytes.

These are fast (no browser): the upload path is plain Flask + Pillow. The
browser half — that the reason reaches `#form-errors` through a real file
picker — is `tests/e2e/test_form_feedback.py`.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _png(size=(600, 400), colour=(180, 60, 40)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, format="PNG")
    return buf.getvalue()


def _post(client, blob: bytes, name: str, mime: str):
    return client.post(
        "/api/photo",
        data={"photo": (io.BytesIO(blob), name, mime)},
        content_type="multipart/form-data",
    )


# The mimetype a real browser sends is derived from the extension, so every
# case here claims to be an image — that is the whole point of the defect.
NOT_IMAGES = [
    pytest.param(b"just some notes, not a photo at all", "shot.png", "image/png",
                 id="text-renamed-to-png"),
    pytest.param(b"", "empty.png", "image/png", id="empty-file"),
    pytest.param(b"\xff\xd8", "half.jpg", "image/jpeg", id="two-byte-jpeg"),
    pytest.param(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n", "cv.png", "image/png",
                 id="pdf-renamed-to-png"),
]


@pytest.mark.parametrize("blob,name,mime", NOT_IMAGES)
def test_a_file_that_is_not_an_image_is_rejected_not_a_500(client, blob, name, mime):
    resp = _post(client, blob, name, mime)
    assert resp.status_code == 415, f"{name} answered {resp.status_code}"
    assert resp.is_json, "the builder reads `error`; an HTML page tells it nothing"
    assert "not a photo" in resp.get_json()["error"]


def test_a_truncated_photo_is_rejected_not_a_500(client):
    """The nastiest case: the PNG header is valid, so `Image.open()` succeeds
    and the failure only surfaces once the pixels are actually read. A guard
    that opens without decoding would let this one through."""
    good = _png()
    resp = _post(client, good[: len(good) // 2], "interrupted.png", "image/png")
    assert resp.status_code == 415, f"answered {resp.status_code}"
    assert "damaged" in resp.get_json()["error"]


def test_the_two_rejections_do_not_give_the_same_advice(client):
    """"Pick a different format" and "that file is broken" are different
    problems with different fixes; collapsing them would leave the user of a
    half-copied photo hunting for a converter."""
    good = _png()
    broken = _post(client, good[: len(good) // 2], "x.png", "image/png")
    wrong = _post(client, b"not an image", "y.png", "image/png")
    assert broken.get_json()["error"] != wrong.get_json()["error"]


def test_an_honest_non_image_extension_is_still_refused(client):
    """The original mimetype gate still earns its place — it rejects without
    reading the file at all."""
    resp = _post(client, b"plain text", "notes.txt", "text/plain")
    assert resp.status_code == 415
    assert "not a photo" in resp.get_json()["error"]


def test_no_file_at_all_is_a_400_with_a_reason(client):
    resp = client.post("/api/photo", data={}, content_type="multipart/form-data")
    assert resp.status_code == 400
    assert resp.get_json()["error"]


def test_a_real_photo_still_uploads_and_is_cropped_square(client):
    """The guard must not cost the happy path. A non-square source is centre-
    cropped and capped at 512px, as before."""
    resp = _post(client, _png((900, 600)), "portrait.png", "image/png")
    assert resp.status_code == 200, resp.data[:200]
    url = resp.get_json()["url"]
    assert url.startswith("/uploads/") and url.endswith(".jpg")

    served = client.get(url)
    assert served.status_code == 200
    img = Image.open(io.BytesIO(served.data))
    assert img.width == img.height, "centre-crop to a square"
    assert max(img.size) <= 512


def test_a_rejected_upload_leaves_nothing_on_disk(client):
    """A refused file must not become an orphaned .jpg in uploads/ — the write
    happens after the decode, and this pins that ordering."""
    from app.config import UPLOADS_DIR

    before = set(UPLOADS_DIR.glob("*")) if UPLOADS_DIR.exists() else set()
    _post(client, b"not an image", "junk.png", "image/png")
    after = set(UPLOADS_DIR.glob("*")) if UPLOADS_DIR.exists() else set()
    assert before == after
