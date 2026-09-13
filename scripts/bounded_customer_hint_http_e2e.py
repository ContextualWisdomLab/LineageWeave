"""Temporary bounded patch for authenticated Customer Master hint-resolution E2E."""

from pathlib import Path

path = Path("backend/tests/test_api.py")
text = path.read_text(encoding="utf-8")

constant_anchor = '''_LEFTOVER_MAP_COORDINATES_MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "0245_report_leftover_map_coordinates.sql"
)
'''
constant_replacement = constant_anchor + '''_CUSTOMER_HINT_RESOLUTION_MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "0250_source_post_customer_resolution.sql"
)
'''
if text.count(constant_anchor) != 1:
    raise SystemExit(f"expected one migration constant anchor, found {text.count(constant_anchor)}")
text = text.replace(constant_anchor, constant_replacement, 1)

apply_anchor = '''            cur.execute(_LEFTOVER_MAP_EXPLAINED_SHARE_MIGRATION.read_text())
            cur.execute(_LEFTOVER_MAP_COORDINATES_MIGRATION.read_text())
'''
apply_replacement = apply_anchor + '''            cur.execute(_CUSTOMER_HINT_RESOLUTION_MIGRATION.read_text())
'''
if text.count(apply_anchor) != 1:
    raise SystemExit(f"expected one migration apply anchor, found {text.count(apply_anchor)}")
text = text.replace(apply_anchor, apply_replacement, 1)

start_marker = "def test_resolve_customer_hint_creates_and_links_a_corroborated_entity(\n"
end_marker = "\n\ndef test_resolve_customer_hint_requires_post_admin"
if text.count(start_marker) != 1:
    raise SystemExit(f"expected one customer resolution test start, found {text.count(start_marker)}")
start = text.index(start_marker)
end = text.index(end_marker, start)
replacement = '''def test_resolve_customer_hint_persists_only_authorized_resolution_without_rebinding_ownership(
    client, demo_analyst_token, seeded_db, monkeypatch
) -> None:
    """Real bearer + PostgreSQL proof for cross-tenant Customer Master resolution.

    Two private tenants deliberately share one raw source-customer hint. The
    admitted post-admin may resolve only evidence visible through the bearer
    account's corporate/process scope. Corroboration creates catalog identity
    and a separate association for that visible source; it must not rewrite
    either source post's authorization ownership or attach the foreign source.
    """
    from lineageweave.relation_verification import (
        STATUS_CORROBORATED,
        RelationVerificationResult,
    )

    _grant_post_admin(seeded_db["dsn"])
    admin_conn = psycopg2.connect(seeded_db["dsn"])
    try:
        with admin_conn.cursor() as cur:
            cur.execute(
                "update source_post set source_customer_code = %s "
                "where post_id in (%s, %s)",
                (
                    "HINT-CODE-001",
                    seeded_db["own_private_post_id"],
                    seeded_db["other_private_post_id"],
                ),
            )
            cur.execute(
                "select post_id::text, corporate_entity_id::text, "
                "coalesce(process_unit_id::text, '') "
                "from source_post where post_id in (%s, %s)",
                (seeded_db["own_private_post_id"], seeded_db["other_private_post_id"]),
            )
            ownership_before = {
                post_id: (corporate_entity_id, process_unit_id)
                for post_id, corporate_entity_id, process_unit_id in cur.fetchall()
            }
        admin_conn.commit()

        class _FakeResolutionClient:
            available = True

            def resolve(self, hint_code: str, context_text: str) -> str | None:
                assert hint_code == "HINT-CODE-001"
                assert "own" in context_text.lower() or context_text
                return "Northridge Grid"

        class _FakeVerificationClient:
            available = True

            def verify(
                self, organization_name: str, relationship_label: str
            ) -> RelationVerificationResult:
                assert organization_name == "Northridge Grid"
                assert relationship_label == "HINT-CODE-001"
                return RelationVerificationResult(
                    status_code=STATUS_CORROBORATED,
                    evidence_url="https://example.test/northridge-grid",
                )

        monkeypatch.setattr(
            "backend.app.main._customer_hint_resolution_client",
            lambda: _FakeResolutionClient(),
        )
        monkeypatch.setattr(
            "backend.app.main._relation_verification_client",
            lambda: _FakeVerificationClient(),
        )

        response = client.post(
            "/api/customer-master/resolve-hint",
            json={"hint_code": "HINT-CODE-001"},
            headers={"Authorization": f"Bearer {demo_analyst_token}"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["entity_name"] == "Northridge Grid"
        assert body["linked_post_count"] == 1

        with admin_conn.cursor() as cur:
            cur.execute(
                "select entity_name, corporate_entity_code from corporate_entity "
                "where corporate_entity_id = %s",
                (body["corporate_entity_id"],),
            )
            entity_name, entity_code = cur.fetchone()
            assert entity_name == "Northridge Grid"
            assert entity_code.startswith("RESOLVED-")

            cur.execute(
                "select post_id::text, corporate_entity_id::text, "
                "coalesce(process_unit_id::text, '') "
                "from source_post where post_id in (%s, %s)",
                (seeded_db["own_private_post_id"], seeded_db["other_private_post_id"]),
            )
            ownership_after = {
                post_id: (corporate_entity_id, process_unit_id)
                for post_id, corporate_entity_id, process_unit_id in cur.fetchall()
            }
            assert ownership_after == ownership_before

            cur.execute(
                "select post_id::text, resolved_corporate_entity_id::text "
                "from source_post_customer_resolution order by post_id"
            )
            associations = cur.fetchall()
            assert associations == [
                (seeded_db["own_private_post_id"], body["corporate_entity_id"])
            ]
    finally:
        admin_conn.close()
'''
text = text[:start] + replacement.rstrip() + text[end:]
path.write_text(text, encoding="utf-8")
