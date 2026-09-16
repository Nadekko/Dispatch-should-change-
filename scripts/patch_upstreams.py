#!/usr/bin/env python3
"""Idempotent local patches for the cloned upstream repos."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if new.strip() in text:
        print(f"already patched: {path}")
        return
    if old not in text:
        raise SystemExit(f"could not patch {path}: expected snippet not found")
    path.write_text(text.replace(old, new, 1))
    print(f"patched: {path}")


def apply_git_patch(repo: Path, patch: Path, already_applied_needle: str) -> None:
    target = repo / "src/summary/summary/core/celery_worker.py"
    if already_applied_needle in target.read_text():
        print(f"already patched: {patch.name}")
        return
    subprocess.run(
        ["git", "-C", str(repo), "apply", str(patch)],
        check=True,
    )
    print(f"patched: {patch.name}")


def main() -> None:
    replace_once(
        ROOT / "meet/src/backend/meet/settings.py",
        '    CSRF_TRUSTED_ORIGINS = ["http://localhost:8072", "http://localhost:3000"]',
        """    CSRF_TRUSTED_ORIGINS = [
        "http://localhost:8072",
        "http://localhost:3000",
        "http://localhost:3001",
    ]""",
    )
    replace_once(
        ROOT / "dictaphone/src/backend/dictaphone/settings.py",
        '    CSRF_TRUSTED_ORIGINS = ["http://localhost:8072", "http://localhost:3000"]',
        """    CSRF_TRUSTED_ORIGINS = [
        "http://localhost:8072",
        "http://localhost:8073",
        "http://localhost:3000",
        "http://localhost:3002",
    ]""",
    )
    apply_git_patch(
        ROOT / "meet",
        ROOT / "patches/meet-transcribe-wav.patch",
        "_transcode_to_wav",
    )


if __name__ == "__main__":
    main()
