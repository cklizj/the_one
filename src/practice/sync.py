"""Git-based sync for the local DB.

The SQLite DB lives inside the git repo (single user), so it can be used from
any clone. Flow per CLI invocation: pull on startup, commit + push after writes.

All failures are non-fatal (warnings only) so the tool keeps working offline.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import typer

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def repo_root() -> Path:
    try:
        proc = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            out = Path(proc.stdout.strip())
            if out.exists():
                return out
    except Exception:
        pass
    return PROJECT_ROOT


def is_repo() -> bool:
    return (repo_root() / ".git").is_dir()


def in_completion_mode() -> bool:
    """Shell tab completion re-enters the app; never pull/commit then."""
    return bool(os.environ.get("_PRACTICE_COMPLETE"))


def _git(root: Path, *args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return proc.returncode, (proc.stderr or proc.stdout).strip()
    except Exception as exc:
        return 1, str(exc)


def pull() -> None:
    """On startup: fetch + rebase local work on top of the remote."""
    if in_completion_mode() or not is_repo():
        return
    root = repo_root()
    code, err = _git(root, "pull", "--rebase", "--autostash")
    silently_ok = (
        "There is no tracking" in err
        or "could not read Username" in err
        or "Need to specify how to reconcile" in err
    )
    if code != 0 and not silently_ok:
        typer.echo(f"[sync] git pull skipped: {err}", err=True)


def commit_and_push(message: str) -> None:
    """After a write: stage everything, commit if changed, then push."""
    if in_completion_mode() or not is_repo():
        return
    root = repo_root()
    code, err = _git(root, "add", "-A")
    if code != 0:
        typer.echo(f"[sync] git add failed: {err}", err=True)
        return
    code, out = _git(root, "status", "--porcelain")
    if code != 0 or not out.strip():
        return  # nothing changed -> no commit/push noise
    code, err = _git(root, "commit", "-m", message)
    if code != 0:
        typer.echo(f"[sync] git commit failed: {err}", err=True)
        return
    code, err = _git(root, "remote", "get-url", "origin")
    if code != 0:
        typer.echo(f"[sync] committed locally, but no 'origin' remote to push to.")
        return
    code, err = _git(root, "push", "origin", "HEAD")
    if code != 0:
        typer.echo(f"[sync] committed locally, but push failed: {err}", err=True)


def run_gh(*args: str) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["gh", *args], capture_output=True, text=True, timeout=180
        )
        return proc.returncode, proc.stdout.strip(), (proc.stderr or proc.stdout).strip()
    except Exception as exc:
        return 1, "", str(exc)