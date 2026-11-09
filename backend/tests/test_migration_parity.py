"""Migration-chain parity checks (ticket 3).

The remote staging comparison needs a database URL, so CI always runs the
manifest check and the matching logic is exercised with synthetic rows.
"""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_migration_parity.py"
SPEC = importlib.util.spec_from_file_location("check_migration_parity", SCRIPT)
parity = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(parity)


def _write_chain(root: Path, names):
    migrations = root / "backend" / "migrations"
    migrations.mkdir(parents=True)
    for name in names:
        (migrations / name).write_text("-- migration", encoding="utf-8")
    manifest = "\n".join(f"--   {name}" for name in names)
    (root / "backend" / "schema.sql").write_text(
        "-- InvoiAI V2 schema manifest\n" + manifest + "\n", encoding="utf-8"
    )


def test_repository_manifest_matches_migration_chain():
    ok, messages = parity.check_manifest(SCRIPT.parents[1])

    assert ok, messages


def test_manifest_drift_reports_missing_and_extra_entries(tmp_path):
    _write_chain(
        tmp_path,
        ["20260101_first.sql", "20260102_second.sql"],
    )
    (tmp_path / "backend" / "migrations" / "20260103_untracked.sql").write_text(
        "-- migration", encoding="utf-8"
    )
    manifest = tmp_path / "backend" / "schema.sql"
    manifest.write_text(
        manifest.read_text(encoding="utf-8") + "--   20260104_missing_file.sql\n",
        encoding="utf-8",
    )

    ok, messages = parity.check_manifest(tmp_path)

    assert not ok
    report = "\n".join(messages)
    assert "20260103_untracked.sql" in report
    assert "20260104_missing_file.sql" in report


def test_remote_rows_match_names_when_dates_collide():
    files = [
        "20260927_document_intake_explicit_processing.sql",
        "20260927_document_type_intake_recognition.sql",
        "20261009_vendor_credits.sql",
    ]

    ok, messages = parity.check_remote(
        files,
        [
            ("20260927", "document_intake_explicit_processing"),
            ("20260927", "document_type_intake_recognition"),
            ("20261009", "vendor_credits"),
        ],
    )

    assert ok, messages


def test_remote_rows_report_pending_and_unknown_migrations():
    files = ["20261009_vendor_credits.sql", "20261010_ap_email_intake_idempotency.sql"]

    ok, messages = parity.check_remote(
        files,
        [("20261009", "vendor_credits"), ("20260101", "legacy_unknown")],
    )

    assert not ok
    report = "\n".join(messages)
    assert "20261010_ap_email_intake_idempotency.sql" in report
    assert "legacy_unknown" in report
