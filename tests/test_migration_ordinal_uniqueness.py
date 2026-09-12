from collections import defaultdict
from pathlib import Path
import subprocess


_ROOT = Path(__file__).resolve().parents[1]
_MIGRATIONS = _ROOT / "migrations"
_ALIAS_PREFIX = "-- lineageweave-compatibility-alias-of: "


def _alias_target(migration: Path) -> str | None:
    first_line = migration.read_text(encoding="utf-8").splitlines()[0]
    if first_line.startswith(_ALIAS_PREFIX):
        return first_line.removeprefix(_ALIAS_PREFIX).strip()
    return None


def _sql_body(migration: Path) -> str:
    return "\n".join(
        line
        for line in migration.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("--")
    ).strip()


def test_canonical_forward_migration_ordinals_are_unique() -> None:
    """Each canonical forward migration owns one four-digit ordinal."""
    by_ordinal: dict[str, list[str]] = defaultdict(list)
    aliases: dict[str, str] = {}
    for migration in sorted(_MIGRATIONS.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        if target := _alias_target(migration):
            aliases[migration.name] = target
            continue
        by_ordinal[migration.name[:4]].append(migration.name)

    duplicates = {
        ordinal: names
        for ordinal, names in by_ordinal.items()
        if len(names) > 1
    }
    assert not duplicates, (
        "duplicate canonical forward migration ordinals make identity ambiguous: "
        f"{duplicates}"
    )

    for alias_name, target_name in aliases.items():
        alias = _MIGRATIONS / alias_name
        target = _MIGRATIONS / target_name
        assert target.exists(), f"migration alias target is missing: {alias_name} -> {target_name}"
        assert _alias_target(target) is None, f"migration alias chain is forbidden: {target_name}"
        assert alias_name[:4] != target_name[:4], (
            f"migration alias must move to a distinct canonical ordinal: {alias_name}"
        )
        assert _sql_body(alias) == _sql_body(target), (
            f"historical migration alias diverged from canonical SQL: {alias_name} -> {target_name}"
        )

        alias_rollback = _MIGRATIONS / "rollback" / alias_name
        target_rollback = _MIGRATIONS / "rollback" / target_name
        assert alias_rollback.exists(), f"historical rollback is missing: {alias_name}"
        assert target_rollback.exists(), f"canonical rollback is missing: {target_name}"
        assert _sql_body(alias_rollback) == _sql_body(target_rollback), (
            f"historical rollback diverged from canonical rollback: {alias_name} -> {target_name}"
        )


def test_migration_replay_skips_declared_compatibility_aliases() -> None:
    """Replay executes the unique canonical migration rather than its alias."""
    script_path = _ROOT / "docker" / "postgres-init" / "migrate.sh"
    script = script_path.read_text(encoding="utf-8")

    assert "first_line=$(sed -n '1p' \"$migration\")" in script
    assert "-- lineageweave-compatibility-alias-of: " in script
    assert "Skipping compatibility alias %s" in script
    subprocess.run(["sh", "-n", str(script_path)], check=True)
