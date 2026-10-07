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
