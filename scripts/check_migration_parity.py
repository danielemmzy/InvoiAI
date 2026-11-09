#!/usr/bin/env python3
"""Check the canonical migration chain and compare it with staging.

Ticket 3 makes ``backend/migrations`` the only migration authority. This
script has two independent checks:

1. ``backend/schema.sql`` (the manifest) lists exactly the migration files in
   ``backend/migrations``.
2. When a staging database URL is available, the migrations recorded in
   ``supabase_migrations.schema_migrations`` match the repository chain.

The remote check uses the standard Supabase migration-history table and the
``psql`` client, so it adds no Python runtime dependency. If no URL is
configured the remote check is reported as skipped rather than silently
passing as if staging had been verified.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

MANIFEST_ENTRY = re.compile(r"^--\s+(\d{8}_[A-Za-z0-9_]+\.sql)\s*$")
MIGRATION_FILE = re.compile(r"^\d{8}_[A-Za-z0-9_]+\.sql$")
DATABASE_URL_ENV = "STAGING_DATABASE_URL"


def migration_files(repo_root: Path) -> list[str]:
    directory = repo_root / "backend" / "migrations"
    return sorted(path.name for path in directory.iterdir() if path.is_file() and MIGRATION_FILE.match(path.name))


def manifest_entries(repo_root: Path) -> list[str]:
    manifest = repo_root / "backend" / "schema.sql"
    entries: list[str] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = MANIFEST_ENTRY.match(line)
        if match:
            entries.append(match.group(1))
    return entries


def check_manifest(repo_root: Path) -> tuple[bool, list[str]]:
    files = migration_files(repo_root)
    manifest = manifest_entries(repo_root)
    messages: list[str] = []

    if files == manifest:
        messages.append(f"manifest OK: {len(files)} migrations listed in lexical order")
        return True, messages

    missing_from_manifest = sorted(set(files) - set(manifest))
    missing_from_disk = sorted(set(manifest) - set(files))
    messages.append("manifest DRIFT detected")
    for name in missing_from_manifest:
        messages.append(f"  file present but not in manifest: {name}")
    for name in missing_from_disk:
        messages.append(f"  manifest entry has no file: {name}")
    if not missing_from_manifest and not missing_from_disk:
        messages.append("  entries exist but are not in lexical order")
    return False, messages


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _remote_migrations(database_url: str) -> list[tuple[str, str]]:
    psql = shutil.which("psql")
    if psql is None:
        raise RuntimeError("psql was not found on PATH; install the PostgreSQL client")

    query = "select version, coalesce(name, '') from supabase_migrations.schema_migrations order by version"
    result = subprocess.run(
        [psql, database_url, "-At", "-F", "\t", "-c", query],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        # Do not echo the URL or the full command: it may contain a password.
        detail = (result.stderr or "").strip().splitlines()
        reason = detail[-1] if detail else "psql exited with an error"
        raise RuntimeError(reason)

    rows: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        version, _, name = line.partition("\t")
        rows.append((version.strip(), name.strip()))
    return rows


def check_remote(files: list[str], rows: list[tuple[str, str]]) -> tuple[bool, list[str]]:
    expected = {Path(name).stem: _normalise(Path(name).stem) for name in files}
    unmatched_remote: list[tuple[str, str]] = []
    applied: set[str] = set()

    for version, name in rows:
        candidates = {_normalise(version), _normalise(name), _normalise(f"{version}_{name}")}
        matched = {
            stem
            for stem, normalised_stem in expected.items()
            if normalised_stem in candidates
            or (normalised_stem.startswith(_normalise(version)) and normalised_stem.endswith(_normalise(name)))
        }
        if matched:
            applied.update(matched)
        else:
            unmatched_remote.append((version, name))

    pending = sorted(set(files) - {name for name in files if Path(name).stem in applied})
    extra = sorted(unmatched_remote)
    messages: list[str] = []

    if not pending and not extra:
        messages.append(f"staging OK: {len(rows)} applied migrations match the repository chain")
        return True, messages

    messages.append("staging DRIFT detected")
    for name in pending:
        messages.append(f"  migration not applied in staging: {name}")
    for version, name in extra:
        messages.append(f"  staging has a migration unknown to this repository: {version} {name}".rstrip())
    return False, messages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="Repository root (defaults to the parent of scripts/).",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get(DATABASE_URL_ENV),
        help=f"Staging PostgreSQL URL. Defaults to ${DATABASE_URL_ENV}.",
    )
    args = parser.parse_args()

    files = migration_files(args.repo_root)
    if not files:
        print("[FAIL] no migrations found under backend/migrations")
        return 1

    manifest_ok, messages = check_manifest(args.repo_root)
    for message in messages:
        print(f"[{'OK' if manifest_ok else 'DRIFT'}] {message}")
    if not manifest_ok:
        return 1

    if not args.database_url:
        print(
            f"[SKIP] staging comparison: set ${DATABASE_URL_ENV} (and install psql) "
            "to compare applied migrations with this chain"
        )
        return 0

    try:
        rows = _remote_migrations(args.database_url)
    except RuntimeError as exc:
        print(f"[FAIL] staging comparison could not run: {exc}")
        return 2

    remote_ok, remote_messages = check_remote(files, rows)
    for message in remote_messages:
        print(f"[{'OK' if remote_ok else 'DRIFT'}] {message}")
    return 0 if remote_ok else 1


if __name__ == "__main__":
    sys.exit(main())
