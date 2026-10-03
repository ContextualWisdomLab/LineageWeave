"""CI-runnable Customer Master hint response-shape contract."""

from backend.app.main import _serialize_customer_hint


_PROVENANCE = (
    "source_post.source_customer_code/source_post.source_customer_name/"
    "source_post_customer_resolution.resolved_corporate_entity_id"
)


def test_unresolved_customer_hint_keeps_explicit_resolution_shape() -> None:
    """Unresolved hints keep nullable resolution fields in the public contract."""
    row = {
        "customer_code": "TEST-CUSTOMER-001",
        "customer_name": None,
        "post_count": 1,
        "related_posts": '[{"post_id":"post-1","post_title":"Public post"}]',
        "verification_status_code": None,
        "resolved_corporate_entity_id": None,
        "resolved_entity_name": None,
        "verification_evidence_url": None,
    }

    assert _serialize_customer_hint(row) == {
        "customer_code": "TEST-CUSTOMER-001",
        "customer_name": None,
        "post_count": 1,
        "related_posts": [{"post_id": "post-1", "post_title": "Public post"}],
        "resolution_status": "hint_only",
        "resolved_corporate_entity_id": None,
        "resolved_entity_name": None,
        "verification_evidence_url": None,
        "hint_trust": "normal",
        "provenance": _PROVENANCE,
    }


def test_resolved_customer_hint_serializes_one_coherent_resolution_row() -> None:
    """Resolved hints expose the selected resolution row without dropping evidence."""
    row = {
        "customer_code": "HINT-CODE-001",
        "customer_name": "Northridge Grid",
        "post_count": 2,
        "related_posts": [{"post_id": "post-2", "post_title": "Grid update"}],
        "verification_status_code": "corroborated",
        "resolved_corporate_entity_id": "corp-1",
        "resolved_entity_name": "Northridge Grid",
        "verification_evidence_url": "https://example.test/northridge-grid",
    }

    result = _serialize_customer_hint(row)

    assert result["resolution_status"] == "corroborated"
    assert result["resolved_corporate_entity_id"] == "corp-1"
    assert result["resolved_entity_name"] == "Northridge Grid"
    assert result["verification_evidence_url"] == "https://example.test/northridge-grid"
    assert result["provenance"] == _PROVENANCE
