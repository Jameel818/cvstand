"""Install the repo's git hooks (feature/download-lock, 2026-11-26).

    python tools/install_hooks.py            # install / refresh
    python tools/install_hooks.py --check    # exit 1 if a hook is missing or out of date

Copies tools/hooks/<name> into the repo's hooks folder (`git rev-parse
--git-path hooks`, so core.hooksPath and worktrees are respected). Today that is
one hook, pre-commit: the download-lock test (tests/test_download_lock.py,
tier 1, ~3.5 min), which refuses the commit if any approved download moved.

A different hook already in place is kept as <name>.local-backup before it is
replaced; re-running is a no-op.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "tools" / "hooks"
HOOKS = ("pre-commit",)


def hooks_dir(repo: Path = ROOT) -> Path:
    out = subprocess.run(["git", "rev-parse", "--git-path", "hooks"], cwd=repo,
                         capture_output=True, text=True, check=True).stdout.strip()
    p = Path(out)
    return p if p.is_absolute() else (repo / p)


def install(repo: Path = ROOT, check: bool = False) -> int:
    dest = hooks_dir(repo)
    bad = 0
    for name in HOOKS:
        src, dst = SOURCE / name, dest / name
        want = src.read_bytes().replace(b"\r\n", b"\n")
        if dst.exists() and dst.read_bytes() == want:
            print(f"{name}: up to date ({dst})")
            continue
        if check:
            print(f"{name}: {'out of date' if dst.exists() else 'MISSING'} ({dst})")
            bad += 1
            continue
        dest.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            backup = dst.with_name(name + ".local-backup")
            shutil.copy2(dst, backup)
            print(f"{name}: the existing hook was kept as {backup.name}")
        dst.write_bytes(want)           # LF endings: sh reads it on Windows too
        os.chmod(dst, os.stat(dst).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"{name}: installed ({dst})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(install(check="--check" in sys.argv[1:]))
