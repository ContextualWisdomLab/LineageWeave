"""Independent per-post customer derivation; all fixtures are synthetic."""
import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app import customer_hint_ingestion as ingestion
from lineageweave.relation_verification import STATUS_CORROBORATED
from tests.test_customer_hint_ingestion import _Client, _Connection, _Pool, _resolve


class _AssociationConnection(_Connection):
    """Track actual association writes and their post identities."""

    def __init__(self, rows):
        super().__init__(sample_rows=rows)
        self.associations = {}

    async def fetch(self, query, *args):
        if "for share" in query.lower():
            return [dict(row) for row in self._sample_rows if row["post_id"] in args[3]]
        if "insert into source_post_customer_resolution" in query:
            self.associations.update({p: args[1] for p in args[0]})
            return [{"post_id": p} for p in args[0]]
        return await super().fetch(query, *args)


def test_identity_cannot_be_copied_from_neighbor_without_own_corroboration(monkeypatch):
    """A is unbound when only B independently supports the identity, even after B deletion."""
    rows = [
        {"post_id": "a", "post_title": "Synthetic A", "post_body": "No identity"},
        {"post_id": "b", "post_title": "Synthetic B", "post_body": "Northridge Grid"},
    ]
    conn = _AssociationConnection(rows)
    contexts = []

    def corroborate(_hint, context, *_clients):
        contexts.append(context)
        if "Northridge Grid" not in context:
            return None
        return SimpleNamespace(resolved_organization_name="Northridge Grid",
                               verification_status_code=STATUS_CORROBORATED,
                               verification_evidence_url="https://evidence.example/synthetic")

    monkeypatch.setattr(ingestion, "resolve_and_verify_organization_name", corroborate)
    result = asyncio.run(_resolve(_Pool(conn), _Client()))
    assert result["linked_post_count"] == 1
    assert conn.associations == {"b": "new-entity-id"}
    assert contexts == ["Synthetic A\nNo identity", "Synthetic B\nNorthridge Grid"]
    # Deleting B removes its association; A never held B-derived data to replay.
    conn.associations.pop("b")
    assert conn.associations == {}


def test_independently_corroborated_posts_retain_their_own_associations(monkeypatch):
    """Positive: two independently supported bindings survive unrelated source removal."""
    rows = [{"post_id": p, "post_title": f"Synthetic {p}", "post_body": "Northridge Grid"}
            for p in ("a", "b")]
    conn = _AssociationConnection(rows)
    contexts = []

    def corroborate(_hint, context, *_clients):
        contexts.append(context)
        return SimpleNamespace(resolved_organization_name="Northridge Grid",
                               verification_status_code=STATUS_CORROBORATED,
                               verification_evidence_url="https://evidence.example/synthetic")

    monkeypatch.setattr(ingestion, "resolve_and_verify_organization_name", corroborate)
    result = asyncio.run(_resolve(_Pool(conn)))
    assert result["linked_post_count"] == 2
    assert len(contexts) == 2
    assert all("---" not in context for context in contexts)
    conn.associations.pop("b")
    assert conn.associations == {"a": "new-entity-id"}


@pytest.mark.parametrize("field", ["post_title", "post_body", "body_tail"])
def test_customer_content_edit_during_verification_rejects_stale_identity(monkeypatch, field):
    """Digest changes, including beyond excerpt length, deny persistence entirely."""
    row = {"post_id": "a", "post_title": "Synthetic title", "post_body": "Northridge Grid",
           "source_content_digest": "a" * 64}
    conn = _AssociationConnection([row])
    row = conn._sample_rows[0]

    def corroborate(*_args):
        row["source_content_digest"] = "b" * 64
        if field != "body_tail":
            row[field] = "Synthetic edited evidence"
        return SimpleNamespace(resolved_organization_name="Northridge Grid",
                               verification_status_code=STATUS_CORROBORATED,
                               verification_evidence_url="https://evidence.example/synthetic")

    monkeypatch.setattr(ingestion, "resolve_and_verify_organization_name", corroborate)
    assert asyncio.run(_resolve(_Pool(conn))) is None
    assert conn.associations == {}


def test_customer_read_requires_exact_current_content_provenance():
    """GET cannot present an old association as derived from newly edited content."""
    source = (Path(__file__).resolve().parents[1] / "backend/app/main.py").read_text()
    join = source.split("left join source_post_customer_resolution resolution", 1)[1].split("where", 1)[0]
    assert "resolution.source_content_digest" in join
    assert "sha256" in join and "post_title" in join and "post_body" in join
