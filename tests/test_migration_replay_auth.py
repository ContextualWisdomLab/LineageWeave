"""Executable authentication contract for the production migration replay script."""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("password", "inherited_password"),
    [(None, None), ("synthetic-rehearsal-password", None), (None, "synthetic-inherited-password")],
)
def test_replay_preserves_libpq_authentication(tmp_path, password, inherited_password) -> None:
    """Replay accepts a password file without inventing or exposing a password."""
    executable_dir = tmp_path / "bin"
    executable_dir.mkdir()
    for name, body in {
        "pg_isready": "#!/bin/sh\nexit 0\n",
        "psql": "#!/bin/sh\nset -eu\n[ \"${PGPASSWORD-}\" = \"$EXPECTED_PASSWORD\" ]\n[ \"$PGPASSFILE\" = /synthetic/rehearsal.pgpass ]\n",
    }.items():
        executable = executable_dir / name
        executable.write_text(body, encoding="utf-8")
        executable.chmod(0o755)
    migration_root = tmp_path / "migrations"
    migration_root.mkdir()
    (migration_root / "0012_synthetic.sql").write_text("SELECT 1;\n", encoding="utf-8")
    environment = {
        key: value for key, value in os.environ.items()
        if key not in {"POSTGRES_PASSWORD", "PGPASSWORD"}
    }
    environment.update({
        "PATH": f"{executable_dir}:{os.defpath}",
        "POSTGRES_USER": "synthetic",
        "POSTGRES_DB": "synthetic",
        "PGPASSFILE": "/synthetic/rehearsal.pgpass",
        "EXPECTED_PASSWORD": password or inherited_password or "",
    })
    if password:
        environment["POSTGRES_PASSWORD"] = password
    if inherited_password:
        environment["PGPASSWORD"] = inherited_password
    script = Path(__file__).resolve().parents[1] / "docker/postgres-init/migrate.sh"

    result = subprocess.run(
        ["sh", str(script), str(migration_root)], env=environment,
        capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Applying 0012_synthetic.sql" in result.stdout
    assert not password or password not in result.stdout + result.stderr
    assert not inherited_password or inherited_password not in result.stdout + result.stderr
