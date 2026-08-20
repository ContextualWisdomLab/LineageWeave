from pathlib import Path

from backend.app.api_key_registry import API_KEY_PREFIX, digest_api_key, issue_api_key


def test_issued_key_is_high_entropy_and_only_digest_is_persistable() -> None:
    issued = issue_api_key()
    assert issued.value.startswith(API_KEY_PREFIX)
    assert issued.key_prefix == issued.value[: len(API_KEY_PREFIX) + 8]
    assert issued.secret_digest == digest_api_key(issued.value)
    assert issued.value not in issued.secret_digest
    assert len(issued.secret_digest) == 64


def test_api_key_schema_is_normalized_and_does_not_store_secret_json() -> None:
    sql = Path("migrations/0051_api_client_key_registry.sql").read_text()
    assert "secret_digest" in sql
    assert "api_client_key_scope" in sql
    assert "api_client_key_event" in sql
    assert "secret_value" not in sql
    assert "jsonb" not in sql.lower()
    assert "text[]" not in sql.lower()


def test_migration_runner_includes_api_key_registry() -> None:
    runner = Path("docker/postgres-init/migrate.sh").read_text()
    assert "0051_*)" in runner
