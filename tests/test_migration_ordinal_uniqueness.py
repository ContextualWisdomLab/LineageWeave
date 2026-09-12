from collections import defaultdict
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_MIGRATIONS = _ROOT / "migrations"


def test_forward_migration_ordinals_are_unique() -> None:
    """Canonical forward migrations must have one filename per four-digit ordinal."""
    by_ordinal: dict[str, list[str]] = defaultdict(list)
    for migration in sorted(_MIGRATIONS.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        by_ordinal[migration.name[:4]].append(migration.name)

    duplicates = {
        ordinal: names
        for ordinal, names in by_ordinal.items()
        if len(names) > 1
    }

    assert not duplicates, (
        "duplicate forward migration ordinals make migration identity ambiguous: "
        f"{duplicates}"
    )
