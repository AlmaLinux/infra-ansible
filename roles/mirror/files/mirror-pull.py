#!/usr/bin/env python3
# Managed by Ansible — do not edit on target hosts; changes will be overwritten.
# Source: infra-ansible/roles/mirror/files/mirror-pull.py
"""Pull repository content from an upstream raw repo into this rsync server.

Triggered via systemd (mirror-pull.service), which is itself started over SSH
from the upstream raw repo host when there is new content to publish. Replaces
the slower push-from-raw model with a pull driven by the rsync server.

All settings come from a JSON config file (default: /etc/mirror-pull/config.json,
override with --config). Output goes to stdout/stderr, which systemd captures
into the journal. A structured summary of the most recent run is written
atomically to the configured status_file so the orchestrator on the upstream
host can confirm success without parsing the journal.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import IO, Any

DEFAULT_CONFIG_PATH = "/etc/mirror-pull/config.json"

# Status sentinel values written into the status file and shown in logs.
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"

# Serialize log output across threads so lines from parallel repo syncs do
# not get spliced together.
_log_lock = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str, prefix: str = "") -> None:
    line = f"[{now_iso()}] {prefix}{msg}"
    with _log_lock:
        print(line, flush=True)


def _pump_stream(stream: IO[str], prefix: str) -> None:
    """Read lines from a Popen pipe and forward them through log() with the
    given prefix. Runs in a daemon thread per stream."""
    try:
        for line in iter(stream.readline, ""):
            if not line:
                break
            log(line.rstrip("\n"), prefix=prefix)
    finally:
        try:
            stream.close()
        except Exception:
            pass


def load_config(path: str) -> dict[str, Any]:
    """Load and validate the JSON config file."""
    try:
        with open(path) as f:
            cfg = json.load(f)
    except FileNotFoundError:
        log(f"config file not found: {path}")
        sys.exit(2)
    except json.JSONDecodeError as exc:
        log(f"config file {path} is not valid JSON: {exc}")
        sys.exit(2)

    required_top = ("source_url", "rsync_bin", "lockfile", "status_file", "repos")
    missing = [k for k in required_top if k not in cfg]
    if missing:
        log(f"config {path} missing required keys: {missing}")
        sys.exit(2)

    cfg.setdefault("rsync_options", [])
    cfg.setdefault("global_excludes", [])
    cfg.setdefault("max_parallel_repos", 0)
    cfg.setdefault("sync_requested_file", "")

    if not isinstance(cfg["max_parallel_repos"], int) or cfg["max_parallel_repos"] < 0:
        log(f"config {path}: 'max_parallel_repos' must be a non-negative integer")
        sys.exit(2)

    if not isinstance(cfg["repos"], list):
        log(f"config {path}: 'repos' must be a list")
        sys.exit(2)

    for i, repo in enumerate(cfg["repos"]):
        for k in ("name", "src", "dest"):
            if k not in repo:
                log(f"config {path}: repos[{i}] missing required field {k!r}")
                sys.exit(2)
        repo.setdefault("excludes", [])

    return cfg


def write_status(status_path: str, status: dict[str, Any]) -> None:
    """Atomically write the status JSON to status_path."""
    parent = os.path.dirname(status_path) or "."
    try:
        os.makedirs(parent, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".last-run.", suffix=".json", dir=parent)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(status, f, indent=2, sort_keys=True)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.chmod(tmp, 0o644)
            os.replace(tmp, status_path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    except OSError as exc:
        log(f"failed to write status file {status_path}: {exc}")


@contextmanager
def file_lock(path: str):
    """Non-blocking exclusive flock; yields True if acquired, False if not."""
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
    acquired = False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except BlockingIOError:
            yield False
            return
        os.ftruncate(fd, 0)
        os.write(fd, f"{os.getpid()}\n".encode())
        yield True
    finally:
        if acquired:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                pass
        os.close(fd)


def _consume_flag(path: str) -> bool:
    """Remove the sync-requested flag file if it exists.

    Return True if the flag was present (i.e. a sync was requested).
    """
    try:
        os.unlink(path)
        return True
    except FileNotFoundError:
        return False


def sync_repo(cfg: dict[str, Any], repo: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    src = cfg["source_url"].rstrip("/") + "/" + repo["src"].lstrip("/")
    if not src.endswith("/"):
        src += "/"
    dest = repo["dest"]
    if not dest.endswith("/"):
        dest += "/"

    os.makedirs(dest, exist_ok=True)

    excludes: list[str] = list(cfg["global_excludes"]) + list(repo.get("excludes") or [])
    cmd: list[str] = [cfg["rsync_bin"], *cfg["rsync_options"]]
    cmd.extend(f"--exclude={pat}" for pat in excludes)
    if dry_run:
        cmd.append("--dry-run")
    cmd.extend([src, dest])

    prefix = f"[{repo['name']}] "
    log(
        f"sync start  src={src} dest={dest} excludes={len(excludes)}",
        prefix=prefix,
    )
    start_iso = now_iso()
    start = time.monotonic()

    # Pipe rsync's stdout/stderr through reader threads so each line can be
    # tagged with [reponame] — keeps logs attributable when repos run in
    # parallel.
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    pumps = [
        threading.Thread(
            target=_pump_stream, args=(proc.stdout, prefix), daemon=True,
        ),
        threading.Thread(
            target=_pump_stream, args=(proc.stderr, prefix), daemon=True,
        ),
    ]
    for t in pumps:
        t.start()
    rc = proc.wait()
    for t in pumps:
        t.join()

    elapsed = time.monotonic() - start
    end_iso = now_iso()
    log(f"sync end    rc={rc} elapsed={elapsed:.1f}s", prefix=prefix)
    return {
        "name": repo["name"],
        "src": src,
        "dest": dest,
        "excludes": excludes,
        "start_time": start_iso,
        "end_time": end_iso,
        "duration_seconds": round(elapsed, 1),
        "rsync_rc": rc,
        # rsync 24 = "some files vanished" — benign during active publishing
        "ok": rc in (0, 24),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to JSON config file (default: {DEFAULT_CONFIG_PATH}).",
    )
    parser.add_argument(
        "--repo",
        action="append",
        help="Restrict sync to one or more named repos (default: all).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Pass --dry-run to rsync; no changes written.",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)

    selected: list[dict[str, Any]] = list(cfg["repos"])
    if args.repo:
        wanted = set(args.repo)
        unknown = wanted - {r["name"] for r in selected}
        if unknown:
            log(f"unknown repo(s): {sorted(unknown)}")
            return 2
        selected = [r for r in selected if r["name"] in wanted]

    if not selected:
        log("no repos configured; nothing to do")
        return 0

    # 0 means "all repos in parallel"; otherwise cap at the configured value
    # but never exceed the number of selected repos (no idle workers).
    workers = cfg["max_parallel_repos"] or len(selected)
    workers = min(workers, len(selected))

    flag = cfg.get("sync_requested_file", "")

    overall_start_iso = now_iso()
    overall_start = time.monotonic()
    log(
        f"mirror-pull begin source={cfg['source_url']} "
        f"repos={[r['name'] for r in selected]} dry_run={args.dry_run} "
        f"workers={workers} config={args.config}"
    )

    repo_results: list[dict[str, Any]] = []
    status_value = STATUS_SUCCESS
    exit_code = 0
    run_count = 0

    with file_lock(cfg["lockfile"]) as acquired:
        if not acquired:
            # Deliberately do NOT overwrite the status file: the in-flight run
            # owns it and will write the authoritative result when it finishes.
            # Orchestrators that need in-flight detection should use
            # `systemctl is-active mirror-pull.service` or `start --wait`.
            log(f"another mirror-pull run holds {cfg['lockfile']}; exiting")
            return 0

        # Re-check loop: always sync at least once (we were started for a
        # reason). After each sync, check if a new sync-requested flag was
        # touched during the run — if so, loop and sync again. This ensures
        # triggers from ALBS are never lost even when syncs overlap.
        sync_again = True
        while sync_again:
            if flag:
                _consume_flag(flag)

            run_count += 1
            log(f"sync pass {run_count} starting")

            with ThreadPoolExecutor(
                max_workers=workers, thread_name_prefix="repo",
            ) as ex:
                repo_results = list(
                    ex.map(lambda r: sync_repo(cfg, r, args.dry_run), selected),
                )

            # Check for re-trigger: a new flag means new content was pushed
            # to repo.alma while we were syncing — run again to pick it up.
            sync_again = bool(flag) and os.path.exists(flag)
            if sync_again:
                log("new sync-requested flag detected -- will re-sync")

    failures = [r for r in repo_results if not r["ok"]]
    if failures:
        status_value = STATUS_FAILED
        exit_code = 1
        log(
            "mirror-pull FAILED: "
            + ", ".join(f"{r['name']}(rc={r['rsync_rc']})" for r in failures)
        )
    else:
        log(f"mirror-pull complete: {run_count} sync pass(es), all repos OK")

    write_status(cfg["status_file"], {
        "hostname": socket.gethostname(),
        "status": status_value,
        "exit_code": exit_code,
        "start_time": overall_start_iso,
        "end_time": now_iso(),
        "duration_seconds": round(time.monotonic() - overall_start, 1),
        "source_url": cfg["source_url"],
        "dry_run": args.dry_run,
        "max_parallel_repos": cfg["max_parallel_repos"],
        "parallelism_used": workers,
        "run_count": run_count,
        "requested_repos": [r["name"] for r in selected],
        "repos": repo_results,
    })
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
