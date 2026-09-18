"""Assert the Railway CLI is pointed at THIS project before deploying.

WHY THIS EXISTS

    `railway up` deploys to whatever the working directory is linked to, and
    the CLI will scaffold a NEW project and service rather than refuse when the
    link is missing or stale. It reports success either way.

    On 2026-09-18 that produced a second project, `perfect-illumination`, with
    its own `cvstand` service — Online, no public domain, no volume, no
    variables. Nothing was broken and nothing said anything: the live URL kept
    answering correctly because the real service was untouched, and the smoke
    test kept returning 25/25 because it tests a URL, not a target. An orphaned
    container simply ran, and billed, until a human noticed an extra row in the
    dashboard.

    The failure is the same shape this project keeps finding: a check that
    passes against the right thing while something else is quietly wrong. A
    green deploy says the upload worked. It does not say WHERE.

USE

    venv/Scripts/python tools/verify_deploy_target.py && railway up --detach

    Exits 0 only when the linked project AND service match the constants below.
    Any drift — a relink for inspection that was never restored, a fresh clone,
    a second machine — stops the deploy instead of creating a twin.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys

#: The real project. Checked by ID, not by name: Railway's generated names are
#: interchangeable-looking ("cooperative-healing", "perfect-illumination") and
#: a name is the one field a person can change by accident.
EXPECTED_PROJECT_ID = "62d200c3-bb4f-4496-b2cc-bed76ed953a9"
EXPECTED_PROJECT_NAME = "cooperative-healing"
EXPECTED_SERVICE = "cvstand"
EXPECTED_ENVIRONMENT = "production"


def _railway() -> str:
    """The CLI's real path.

    Two Windows traps, both hit while writing this:

      1. `subprocess` will not resolve the bare name `railway`, because the npm
         global install is a `.cmd` shim. The first version reported "railway
         CLI not found" on a machine where `railway status` had just worked in
         the same shell.
      2. `shutil.which("railway")` then found npm's EXTENSIONLESS Unix shim
         first — a shell script — and running it raised
         "WinError 193: %1 is not a valid Win32 application".

    So the executable forms are tried by name, in order, before the bare one.
    """
    for candidate in ("railway.cmd", "railway.exe", "railway"):
        found = shutil.which(candidate)
        if found:
            return found
    print("FAIL railway CLI not found — npm i -g @railway/cli")
    raise SystemExit(2)


def _status() -> dict:
    try:
        out = subprocess.run(
            [_railway(), "status", "--json"],
            capture_output=True, text=True, timeout=120, check=False,
        )
    except OSError as exc:
        print(f"FAIL could not run the railway CLI: {exc}")
        raise SystemExit(2)
    if out.returncode != 0 or not out.stdout.strip():
        print("FAIL `railway status` returned nothing — not linked, or not "
              "logged in. Run `railway login` then `railway link`.")
        print((out.stderr or "").strip()[:300])
        raise SystemExit(2)
    return json.loads(out.stdout)


def main() -> int:
    st = _status()
    project_id = st.get("id", "")
    project_name = st.get("name", "")

    problems = []
    if project_id != EXPECTED_PROJECT_ID:
        problems.append(
            f"project is {project_name!r} ({project_id}), expected "
            f"{EXPECTED_PROJECT_NAME!r} ({EXPECTED_PROJECT_ID})")

    # The environment and service live under environments[].serviceInstances.
    envs = [e["node"] for e in st.get("environments", {}).get("edges", [])]
    names = {e.get("name") for e in envs}
    if EXPECTED_ENVIRONMENT not in names:
        problems.append(
            f"no {EXPECTED_ENVIRONMENT!r} environment; found {sorted(names)}")

    services = {
        s["node"].get("serviceName") or s["node"].get("name")
        for e in envs
        for s in e.get("serviceInstances", {}).get("edges", [])
    }
    services |= {
        s["node"].get("name")
        for s in st.get("services", {}).get("edges", [])
    }
    services.discard(None)
    if EXPECTED_SERVICE not in services:
        problems.append(
            f"no {EXPECTED_SERVICE!r} service; found {sorted(services)}")

    if problems:
        print("REFUSING TO DEPLOY — the CLI is not pointed at this project:")
        for p in problems:
            print(f"  - {p}")
        print("\n  fix: railway link --project "
              f"{EXPECTED_PROJECT_NAME} --environment {EXPECTED_ENVIRONMENT} "
              f"--service {EXPECTED_SERVICE}")
        return 1

    print(f"OK  linked to {project_name} / {EXPECTED_ENVIRONMENT} / "
          f"{EXPECTED_SERVICE}  ({project_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
