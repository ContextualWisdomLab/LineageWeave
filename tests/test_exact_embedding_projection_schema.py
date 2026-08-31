from pathlib import Path


MIGRATION = Path("migrations/0271_exact_embedding_projection.sql")


def test_exact_projection_is_digest_bound_and_replay_safe() -> None:
    """Projection rows must remain exact, versioned, and natively replayable."""
    sql = MIGRATION.read_text()

    assert "create table if not exists post_content_embedding_exact_projection" in sql
    assert "float8send(value.dimension_value)" in sql
    assert "order by value.dimension_index" in sql
    assert "digest(packed.vector_bytes, 'sha256')" in sql
    assert "octet_length(vector_bytes) = embedding_dimension_count * 8" in sql
    assert "after insert or update or delete" in sql
    assert "refresh_post_content_embedding_exact_projection" in sql
    assert "packed.dimension_count = embedding.embedding_dimension_count" in sql
    assert "if not exists (" in sql
    assert "select 1 from post_content_embedding_exact_projection" in sql
    assert "ivfflat" not in sql.lower()
    assert "hnsw" not in sql.lower()
