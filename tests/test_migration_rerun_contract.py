import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATE_OBJECT = re.compile(
    r"^create\s+(?:unique\s+)?(?:table|index)\s+(.+)$",
    re.IGNORECASE | re.MULTILINE,
)


def _has_unprotected_create(sql: str) -> bool:
    for match in CREATE_OBJECT.finditer(sql):
        target = match.group(1).strip().lower()
        if target.startswith("concurrently "):
            target = target.removeprefix("concurrently ")
        if not target.startswith("if not exists "):
            return True
    return False


def test_post_bootstrap_migrations_create_objects_idempotently() -> None:
    """Every migration replayed by migrate.sh must tolerate a second run."""
    offenders = []
    for migration in sorted((ROOT / "migrations").glob("[0-9][0-9][0-9][0-9]_*.sql")):
        if int(migration.name[:4]) < 12:
            continue
        if _has_unprotected_create(migration.read_text(encoding="utf-8")):
            offenders.append(migration.name)

    assert offenders == []
