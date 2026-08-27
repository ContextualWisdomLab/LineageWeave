"""Static schema guards for the authorized job-architecture contract."""

from pathlib import Path


def test_job_architecture_schema_is_normalized_and_immutable() -> None:
    migration = Path("migrations/0223_authorized_job_architecture.sql").read_text()

    for table in (
        "job_architecture_source",
        "job_architecture_node",
        "job_architecture_hierarchy_edge",
        "job_architecture_occupation_binding",
    ):
        assert f"create table if not exists {table}" in migration
    assert "job_architecture_kind_code in ('job_family', 'job_series')" in migration
    assert "reject_job_architecture_mutation" in migration
    assert "broader_job_architecture_code <> narrower_job_architecture_code" in migration
    assert "occupation_scheme_iri" in migration
