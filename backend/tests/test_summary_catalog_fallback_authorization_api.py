"""Authenticated fallback regressions for summary catalog authorization."""

from __future__ import annotations

import psycopg2
import pytest

from backend.tests import test_api as api_test

client = api_test.client
demo_analyst_token = api_test.demo_analyst_token
seeded_db = api_test.seeded_db
pytestmark = api_test.pytestmark


class _UnavailableSummaryClient:
    """Represent an orchestrator client that cannot serve a summary request."""

    available = False


class _FailingSummaryClient:
    """Represent an available orchestrator whose summary call fails before persistence."""

    available = True

    def summarize(self, post_title: str, post_body: str):
        """Raise a deterministic provider error before catalog persistence begins."""
        raise OSError("synthetic orchestrator failure")


def _shared_catalog_snapshot(dsn: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Capture complete corporate and team catalog rows for mutation detection."""
    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "select row_to_json(c)::text from corporate_entity as c "
                "order by corporate_entity_id"
            )
            corporate_entities = tuple(row[0] for row in cur.fetchall())
            cur.execute(
                "select row_to_json(t)::text from cataloged_team as t order by team_id"
            )
            cataloged_teams = tuple(row[0] for row in cur.fetchall())
    finally:
        conn.close()
    return corporate_entities, cataloged_teams


def _seed_stale_summary(dsn: str, source_post_id: str, *, title: str) -> str:
    """Create one visible post with an intentionally obsolete persisted summary."""
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                "insert into source_post "
                "(author_account_id, corporate_entity_id, post_title, post_body, "
                "voc_type_code, visibility_code) "
                "select author_account_id, corporate_entity_id, %s, %s, 'voc', 'public' "
                "from source_post where post_id = %s returning post_id",
                (title, "fallback authorization evidence body", source_post_id),
            )
            post_id = str(cur.fetchone()[0])
            cur.execute(
                "insert into post_summary_result "
                "(post_id, korean_summary, summary_contract_version) values (%s, %s, %s)",
                (post_id, "오래된 요약 증거", "legacy-fallback-contract"),
            )
    finally:
        conn.close()
    return post_id


@pytest.mark.parametrize("grant_admin", [False, True], ids=["reader", "admin"])
@pytest.mark.parametrize("provider_state", ["unavailable", "failure"])
def test_stale_summary_fallback_never_mutates_shared_catalogs(
    client,
    demo_analyst_token,
    seeded_db,
    monkeypatch,
    grant_admin: bool,
    provider_state: str,
) -> None:
    """Stale continuity must not run shared-catalog enrichment after provider failure."""
    if grant_admin:
        api_test._grant_post_admin(seeded_db["dsn"])

    post_id = _seed_stale_summary(
        seeded_db["dsn"],
        seeded_db["own_private_post_id"],
        title=f"Fallback auth {provider_state} admin={grant_admin}",
    )
    before = _shared_catalog_snapshot(seeded_db["dsn"])

    summary_client = (
        _UnavailableSummaryClient()
        if provider_state == "unavailable"
        else _FailingSummaryClient()
    )
    monkeypatch.setattr("backend.app.main._post_summary_client", lambda: summary_client)

    def forbidden_hierarchy_factory():
        """Fail if a fallback path tries to construct a catalog-mutation capability."""
        raise AssertionError("fallback must not construct hierarchy inference")

    def forbidden_verification_factory():
        """Fail if a fallback path tries to construct a relation-verification capability."""
        raise AssertionError("fallback must not construct relation verification")

    monkeypatch.setattr(
        "backend.app.main._corporate_hierarchy_inference_client",
        forbidden_hierarchy_factory,
    )
    monkeypatch.setattr(
        "backend.app.main._relation_verification_client",
        forbidden_verification_factory,
    )

    response = client.get(
        f"/api/posts/{post_id}/summary",
        headers={"Authorization": f"Bearer {demo_analyst_token}"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["summary_status"] == "stale"
    assert payload["korean_summary"] == "오래된 요약 증거"
    assert _shared_catalog_snapshot(seeded_db["dsn"]) == before
