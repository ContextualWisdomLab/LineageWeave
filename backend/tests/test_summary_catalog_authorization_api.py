"""Authenticated integration proof for summary shared-catalog authorization."""

from __future__ import annotations

import psycopg2

from backend.tests import test_api as api_test
from lineageweave.corporate_hierarchy_inference import HierarchyProposal
from lineageweave.post_summary import (
    ACTOR_TYPE_ORGANIZATION,
    ACTOR_TYPE_TEAM,
    PostSummary,
    RoleResponsibility,
)
from lineageweave.relation_verification import (
    STATUS_CORROBORATED,
    RelationVerificationResult,
)

client = api_test.client
demo_analyst_token = api_test.demo_analyst_token
seeded_db = api_test.seeded_db
pytestmark = api_test.pytestmark


def _shared_catalog_snapshot(dsn: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Capture complete corporate and team catalog state, including hierarchy links."""
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


def test_post_read_summary_materialization_cannot_mutate_shared_catalogs(
    client, demo_analyst_token, seeded_db, monkeypatch
) -> None:
    """post_read may materialize a summary but must not write shared master data."""
    reader_org = "Reader Summary Never Create Corp"
    reader_team = "Reader Summary Never Create Team"
    admin_org = "Admin Summary Create Corp"
    admin_team = "Admin Summary Create Team"

    class _FakeSummaryClient:
        available = True

        def summarize(self, post_title: str, post_body: str) -> PostSummary:
            """Return distinct reader/admin organizations for authorization assertions."""
            if post_title.startswith("Reader summary auth"):
                organization_name, team_name = reader_org, reader_team
            else:
                organization_name, team_name = admin_org, admin_team
            return PostSummary(
                korean_summary="권한 경계를 검증하는 합성 요약입니다.",
                roles_and_responsibilities=(
                    RoleResponsibility(
                        actor_name=organization_name,
                        responsibility="조직 역할",
                        actor_type_code=ACTOR_TYPE_ORGANIZATION,
                    ),
                    RoleResponsibility(
                        actor_name=team_name,
                        responsibility="팀 역할",
                        actor_type_code=ACTOR_TYPE_TEAM,
                        affiliated_organization_name=organization_name,
                    ),
                ),
            )

    hierarchy_factory_calls = 0
    verification_factory_calls = 0

    class _FakeHierarchyInferenceClient:
        available = True

        def infer(self, organization_name: str, context_text: str) -> HierarchyProposal:
            """Return a deterministic company-level hierarchy proposal for admin writes."""
            return HierarchyProposal(level_code="company", parent_name=None)

    class _FakeVerificationClient:
        available = True

        def verify(
            self, organization_name: str, relationship_label: str
        ) -> RelationVerificationResult:
            """Corroborate the synthetic admin organization deterministically."""
            return RelationVerificationResult(
                status_code=STATUS_CORROBORATED,
                evidence_url=f"https://example.org/{organization_name.replace(' ', '-')}",
            )

    def hierarchy_factory():
        """Count construction of mutation-capable hierarchy clients."""
        nonlocal hierarchy_factory_calls
        hierarchy_factory_calls += 1
        return _FakeHierarchyInferenceClient()

    def verification_factory():
        """Count construction of mutation-capable verification clients."""
        nonlocal verification_factory_calls
        verification_factory_calls += 1
        return _FakeVerificationClient()

    monkeypatch.setattr("backend.app.main._post_summary_client", lambda: _FakeSummaryClient())
    monkeypatch.setattr(
        "backend.app.main._corporate_hierarchy_inference_client", hierarchy_factory
    )
    monkeypatch.setattr(
        "backend.app.main._relation_verification_client", verification_factory
    )

    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            post_ids = []
            for title in ("Reader summary auth", "Admin summary auth"):
                cur.execute(
                    "insert into source_post "
                    "(author_account_id, corporate_entity_id, post_title, post_body, "
                    "voc_type_code, visibility_code) "
                    "select author_account_id, corporate_entity_id, %s, %s, 'voc', 'public' "
                    "from source_post where post_id = %s returning post_id",
                    (
                        title,
                        "authorization evidence body",
                        seeded_db["own_private_post_id"],
                    ),
                )
                post_ids.append(str(cur.fetchone()[0]))
            for organization_name in (reader_org, admin_org):
                cur.execute(
                    "select count(*) from corporate_entity where entity_name = %s",
                    (organization_name,),
                )
                assert cur.fetchone()[0] == 0
            for team_name, organization_name in (
                (reader_team, reader_org),
                (admin_team, admin_org),
            ):
                cur.execute(
                    "select count(*) from cataloged_team "
                    "where team_name = %s and affiliated_organization_name = %s",
                    (team_name, organization_name),
                )
                assert cur.fetchone()[0] == 0
    finally:
        admin_conn.close()

    catalog_before_reader = _shared_catalog_snapshot(seeded_db["dsn"])
    headers = {"Authorization": f"Bearer {demo_analyst_token}"}
    reader = client.get(f"/api/posts/{post_ids[0]}/summary", headers=headers)
    assert reader.status_code == 200, reader.text
    assert hierarchy_factory_calls == 0
    assert verification_factory_calls == 0
    assert _shared_catalog_snapshot(seeded_db["dsn"]) == catalog_before_reader

    admin_conn = psycopg2.connect(seeded_db["dsn"])
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "select count(*) from corporate_entity where entity_name = %s",
                (reader_org,),
            )
            assert cur.fetchone()[0] == 0
            cur.execute(
                "select count(*) from cataloged_team "
                "where team_name = %s and affiliated_organization_name = %s",
                (reader_team, reader_org),
            )
            assert cur.fetchone()[0] == 0
            cur.execute(
                "select cataloged_corporate_entity_id, cataloged_team_id "
                "from post_summary_role where post_id = %s",
                (post_ids[0],),
            )
            assert cur.fetchall() == [(None, None), (None, None)]
    finally:
        admin_conn.close()

    api_test._grant_post_admin(seeded_db["dsn"])
    admin = client.get(f"/api/posts/{post_ids[1]}/summary", headers=headers)
    assert admin.status_code == 200, admin.text
    assert hierarchy_factory_calls > 0
    assert verification_factory_calls > 0

    admin_conn = psycopg2.connect(seeded_db["dsn"])
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "select count(*) from corporate_entity where entity_name = %s",
                (admin_org,),
            )
            assert cur.fetchone()[0] == 1
            cur.execute(
                "select count(*) from cataloged_team "
                "where team_name = %s and affiliated_organization_name = %s",
                (admin_team, admin_org),
            )
            assert cur.fetchone()[0] == 1
    finally:
        admin_conn.close()
