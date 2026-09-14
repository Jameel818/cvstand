# CVStand — production image.
#
# WHY NOT THE MICROSOFT PLAYWRIGHT IMAGE
#   `mcr.microsoft.com/playwright/python:vX.Y.Z-noble` ships Chromium and its
#   system libraries preinstalled and builds faster. It also has to match the
#   pinned playwright version EXACTLY, and a tag that does not exist fails the
#   build with a pull error rather than anything descriptive. Installing the
#   browser from the same playwright that requirements.txt pinned keeps the
#   two in step by construction, which is worth two minutes of build time.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUTF8=1 \
    # Where `playwright install` puts Chromium. Set explicitly so the browser
    # lands in a path the runtime user can read -- the default is $HOME-based,
    # and a platform that runs the container as a different user than the one
    # that built it will otherwise "not find" a browser that is present.
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

WORKDIR /app

# Dependencies first, as their own layer: requirements.txt changes far less
# often than the application, so a code edit does not re-download Chromium.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && playwright install --with-deps chromium \
 && rm -rf /var/lib/apt/lists/*

COPY . .

# The résumé documents and the accounts database live here. On Railway this
# path is the mount point of a persistent volume -- WITHOUT one the container
# filesystem is ephemeral and every deploy silently deletes every account.
ENV CVSTAND_DATA_DIR=/data
RUN mkdir -p /data

EXPOSE 8080

# ONE WORKER, THREADS FOR CONCURRENCY — deliberate, not a placeholder.
#
# `app/exporters/pdf.py` launches a whole Chromium per PDF request, and
# `app/limits.py` caps how many may run at once with an in-process
# BoundedSemaphore. That semaphore is per PROCESS: run four workers and the
# real cap is four times what the config says, which is exactly how a small
# box gets OOM-killed under a burst. Threads share the semaphore, so the cap
# means what it says. More throughput than one box gives is the moment to move
# the admission state out of memory, not to raise the worker count.
#
# The timeout is well above RENDER_QUEUE_WAIT (20s) plus a slow render, or
# gunicorn kills a request that is legitimately waiting for its turn.
CMD gunicorn "app:create_app()" \
    --bind "0.0.0.0:${PORT:-8080}" \
    --workers 1 \
    --threads 8 \
    --timeout 120 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile -
