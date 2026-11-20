"""Migration runner tests; subprocess doubles do not prove PostgreSQL behavior."""

import json
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_sql_migrations.sh"


def run_migrations(tmp_path, directory, exit_code=0):
    binary = tmp_path / "psql"
    binary.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "print(json.dumps(sys.argv[1:]))\n"
        "sys.exit(int(os.environ['PSQL_EXIT']))\n"
    )
    binary.chmod(0o755)
    return subprocess.run(
        ["sh", str(RUNNER), str(directory)],
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}",
             "PSQL_EXIT": str(exit_code)},
        capture_output=True, text=True, check=False,
    )


@pytest.mark.parametrize("service", ["identity-service", "farm-service"])
def test_all_service_migrations_are_passed_in_order(tmp_path, service):
    directory = ROOT / "services" / service / "migrations"
    result = run_migrations(tmp_path, directory)
    assert result.returncode == 0
    assert json.loads(result.stdout) == [
        "--no-psqlrc", "--set=ON_ERROR_STOP=1", "--single-transaction",
        *[arg for path in sorted(directory.glob("*.sql"))
          for arg in ("--file", str(path))],
    ]


def test_discovery_handles_spaces_and_ignores_non_sql(tmp_path):
    directory = tmp_path / "migration files"
    directory.mkdir()
    for name in ["020_second.sql", "001_first.sql", "notes.txt"]:
        (directory / name).touch()
    result = run_migrations(tmp_path, directory)
    assert result.returncode == 0
    assert json.loads(result.stdout)[3:] == [
        "--file", str(directory / "001_first.sql"),
        "--file", str(directory / "020_second.sql"),
    ]


@pytest.mark.parametrize("exists", [True, False])
def test_empty_or_missing_directory_fails(tmp_path, exists):
    directory = tmp_path / "migrations"
    if exists:
        directory.mkdir()
    result = run_migrations(tmp_path, directory)
    assert result.returncode != 0
    assert "No SQL migrations found" in result.stderr
    assert not result.stdout


def test_psql_failure_is_propagated(tmp_path):
    directory = tmp_path / "migrations"
    directory.mkdir()
    (directory / "001_fail.sql").touch()
    assert run_migrations(tmp_path, directory, exit_code=3).returncode == 3
