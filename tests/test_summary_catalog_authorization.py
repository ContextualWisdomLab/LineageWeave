"""Authorization contracts for summary-driven shared-catalog enrichment."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from backend.app import main
from backend.app import post_summary_ingestion as summary_ingestion
from backend.app.auth import CurrentAccount


def _account(*permissions: str) -> CurrentAccount:
    """Build a synthetic account with only the permissions under test."""
    return CurrentAccount(
        user_account_id="synthetic-account",
        external_subject_id="synthetic-subject",
        display_name="Synthetic Reader",
        preferred_locale="ko",
        corporate_entity_ids=frozenset({"synthetic-corp"}),
        process_unit_ids=frozenset({"synthetic-pu"}),
        permission_codes=frozenset(permissions),
    )


def test_reader_never_constructs_shared_catalog_clients(monkeypatch) -> None:
    """Keep mutation-capable catalog clients outside the post_read path."""
    captured: dict[str, object] = {}

    async def fake_persist(*_args, **kwargs):
        """Capture the application boundary arguments without touching storage."""
        captured.update(kwargs)
        return {"post_id": "synthetic-post"}

    def forbidden():
        """Fail if a reader attempts to construct a catalog mutation client."""
        raise AssertionError("post_read must not construct mutation-capable clients")

    monkeypatch.setattr(main, "persist_post_summary", fake_persist)
    monkeypatch.setattr(main, "_corporate_hierarchy_inference_client", forbidden)
    monkeypatch.setattr(main, "_relation_verification_client", forbidden)
    asyncio.run(
        main._persist_post_summary_for_account(
            object(),
            "synthetic-post",
            object(),
            post_body="evidence",
            account=_account("post_read"),
        )
    )
    assert captured["allow_catalog_enrichment"] is False
    assert captured["hierarchy_inference_client"].available is False
    assert captured["verification_client"].available is False


def test_admin_retains_explicit_enrichment_capability(monkeypatch) -> None:
    """Permit shared-catalog enrichment only when post_admin is explicit."""
    captured: dict[str, object] = {}
    hierarchy = SimpleNamespace(available=True)
    verification = SimpleNamespace(available=True)

    async def fake_persist(*_args, **kwargs):
        """Capture the admin persistence call without writing synthetic state."""
        captured.update(kwargs)
        return {"post_id": "synthetic-post"}

    monkeypatch.setattr(main, "persist_post_summary", fake_persist)
    monkeypatch.setattr(main, "_corporate_hierarchy_inference_client", lambda: hierarchy)
    monkeypatch.setattr(main, "_relation_verification_client", lambda: verification)
    asyncio.run(
        main._persist_post_summary_for_account(
            object(),
            "synthetic-post",
            object(),
            post_body="evidence",
            account=_account("post_read", "post_admin"),
        )
    )
    assert captured["allow_catalog_enrichment"] is True
    assert captured["hierarchy_inference_client"] is hierarchy
    assert captured["verification_client"] is verification


def test_reader_team_resolution_is_lookup_only(monkeypatch) -> None:
    """Resolve a known team for readers without invoking the upsert owner."""

    class Connection:
        async def fetchrow(self, query, *args):
            """Return the known team only for the parameterized lookup contract."""
            assert query.startswith("select team_id from cataloged_team")
            assert args == ("Synthetic Team", "Synthetic Org")
            return {"team_id": "known-team"}

    async def forbidden_upsert(*_args, **_kwargs):
        """Fail if lookup-only reader resolution crosses into catalog writes."""
        raise AssertionError("post_read must not upsert cataloged_team")

    monkeypatch.setattr(summary_ingestion, "upsert_team", forbidden_upsert)
    team_id = asyncio.run(
        summary_ingestion._resolve_summary_team_id(
            Connection(),
            "Synthetic Team",
            "Synthetic Org",
            [],
            allow_catalog_enrichment=False,
        )
    )
    assert team_id == "known-team"


def test_admin_team_resolution_may_upsert(monkeypatch) -> None:
    """Retain canonical team upsert behavior behind explicit enrichment."""

    async def fake_upsert(_conn, team_name, affiliation, candidates):
        """Return a deterministic team id after checking owner inputs."""
        assert (team_name, affiliation, candidates) == (
            "Synthetic Team",
            "Synthetic Org",
            [],
        )
        return "created-team"

    monkeypatch.setattr(summary_ingestion, "upsert_team", fake_upsert)
    team_id = asyncio.run(
        summary_ingestion._resolve_summary_team_id(
            object(),
            "Synthetic Team",
            "Synthetic Org",
            [],
            allow_catalog_enrichment=True,
        )
    )
    assert team_id == "created-team"


def test_default_summary_persistence_denies_catalog_mutations_even_with_live_clients(monkeypatch) -> None:
    """Actual persistence drops mutation capability while still writing post-owned roles."""
    from contextlib import nullcontext
    from lineageweave.post_summary import (
        ACTOR_TYPE_ORGANIZATION, ACTOR_TYPE_TEAM, PostSummary, RoleResponsibility,
    )
    from backend.app.corporate_entity_ingestion import get_or_create_corporate_entity

    class Connection:
        def __init__(self):
            self.writes = []

        def transaction(self):
            return nullcontext()

        async def fetchrow(self, query, *args):
            assert query.startswith("select team_id from cataloged_team")
            return None

        async def execute(self, query, *args):
            assert "insert into corporate_entity" not in query
            assert "insert into cataloged_team" not in query
            self.writes.append(query)
            return "OK"

    class ForbiddenClient:
        available = True

        def infer(self, *_args):
            raise AssertionError("default summary may not invoke hierarchy inference")

        def verify(self, *_args):
            raise AssertionError("default summary may not invoke catalog verification")

    async def no_candidates(_conn):
        return []

    async def no_aliases(_conn):
        return []

    async def no_edges(_conn, _post_id):
        return []

    async def serialized(_conn, post_id):
        return {"post_id": post_id, "korean_summary": "Synthetic summary"}

    # Retain the canonical corporate resolver; with Null capabilities a new name
    # is an honest miss, not a mutation. Exercise team projection's real lookup.
    monkeypatch.setattr(summary_ingestion, "get_or_create_corporate_entity", get_or_create_corporate_entity)
    monkeypatch.setattr(summary_ingestion, "_load_corporate_entity_candidates", no_candidates)
    monkeypatch.setattr(summary_ingestion, "load_corroborated_organization_name_aliases", no_aliases)
    monkeypatch.setattr(summary_ingestion, "persist_edges_for_post", no_edges)
    monkeypatch.setattr(summary_ingestion, "fetch_persisted_summary", serialized)
    connection = Connection()
    summary = PostSummary(
        korean_summary="Synthetic summary",
        roles_and_responsibilities=(
            RoleResponsibility(actor_name="Synthetic New Org", responsibility="Evidence", actor_type_code=ACTOR_TYPE_ORGANIZATION),
            RoleResponsibility(actor_name="Synthetic New Team", responsibility="Evidence", actor_type_code=ACTOR_TYPE_TEAM),
        ),
    )
    payload = asyncio.run(summary_ingestion.persist_post_summary(
        connection, "synthetic-post", summary,
        hierarchy_inference_client=ForbiddenClient(), verification_client=ForbiddenClient(),
    ))
    assert payload["korean_summary"] == "Synthetic summary"
    assert any("insert into post_summary_role" in query for query in connection.writes)
