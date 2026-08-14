"""Behavior contracts for bounded runtime fallbacks and identity preservation."""

from __future__ import annotations

import hashlib
import urllib.error

import lineageweave as lw
import lineageweave_server as server


class _Connection:
    """Minimal context manager for mutation paths whose SQL calls are asserted elsewhere."""

    def __enter__(self):
        """Return the inert connection object."""
        return self

    def __exit__(self, *_args):
        """Do not suppress exceptions from the exercised product path."""
        return False


def test_bounded_semantic_values_are_json_safe_at_every_supported_shape() -> None:
    """Preserve bounded model metadata without allowing arbitrary object graphs through."""
    assert lw._bounded_semantic_value(None) == ""
    assert lw._bounded_semantic_value(["value"]) == ["value"]
    assert lw._bounded_semantic_value({"outer": {"inner": "value"}})["outer"]["inner"] == "value"
    assert isinstance(lw._bounded_semantic_value(object()), str)


def test_durable_keymen_keep_user_override_and_reject_missing_document(monkeypatch) -> None:
    """Keep an intentional override when a later model snapshot has the same document."""
    assert lw.durable_keyman_record(
        {"keyman_source": "llm", "keyman_our_side": [{"person_name": "No document"}]}
    ) is None

    document_rows = [
        {
            "document_no": "DOC-1",
            "keyman_source": "llm",
            "keyman_our_side": [{"person_name": "Model person"}],
            "keyman_counterpart_side": [],
        }
    ]
    override_rows = [
        {
            "document_no": "DOC-1",
            "keyman_source": "user_override",
            "keyman_our_side": [{"person_name": "Managed person", "rank": "G4", "title": "Lead"}],
            "keyman_counterpart_side": [],
        },
        {
            "document_no": "DOC-1",
            "keyman_source": "llm",
            "keyman_our_side": [{"person_name": "Later model person"}],
            "keyman_counterpart_side": [],
        },
    ]

    def query(_connection, statement, *_args):
        """Return rows from the table selected by the durable loader."""
        return document_rows if lw.ANALYSIS_DOCUMENT_TABLE in statement else override_rows

    monkeypatch.setattr(lw, "_database_table_exists", lambda *_args: True)
    monkeypatch.setattr(lw, "_database_query", query)
    records = lw.load_durable_keymen(object())
    assert records["DOC-1"]["keyman_source"] == "user_override"
    assert records["DOC-1"]["keyman_our_side"][0]["title"] == "Lead"
    normalized = lw.normalize_keyman_side(
        [{"person_name": "Managed person", "node_id": "node-1", "entity_type": "person", "predicate": "related", "relationship_direction": "outbound"}]
    )
    assert normalized[0]["node"] == "node-1"
    assert normalized[0]["direction"] == "outbound"


def test_roles_parser_and_fallback_preserve_identity_qualifiers() -> None:
    """Normalize malformed R&R responses without collapsing org, rank, or title."""
    document = {"document_no": "DOC-1", "first_stage": "L"}
    assert lw.parse_roles_and_responsibilities_response(
        {"roles_and_responsibilities": {"unexpected": True}}, document
    ) == []
    rows = lw.parse_roles_and_responsibilities_response(
        {
            "roles_and_responsibilities": [
                "not a record",
                {"actor_type": "unknown", "role": "ignored", "responsibility": "missing agent"},
                {
                    "actor_type": "person",
                    "person_name": "Same name",
                    "role": "Owner",
                    "responsibility": "Owns the event",
                    "rank": "G4",
                    "title": "Lead",
                    "node": "node-1",
                    "entity": "person",
                    "relationship": "owns",
                    "direction": "outbound",
                },
                {
                    "actor_type": "unknown",
                    "organization_name": "Organization A",
                    "role": "Partner",
                    "responsibility": "Supplies context",
                },
                {
                    "actor_type": "person",
                    "person_name": "Same name",
                    "organization_name": "Organization B",
                    "role": "Reviewer",
                    "responsibility": "Reviews the event",
                    "affiliation_status": "unverified",
                },
                {"actor_type": "person", "person_name": "Incomplete", "responsibility": "No role"},
            ]
        },
        document,
    )
    by_role = {row["role"]: row for row in rows}
    assert by_role["Owner"]["affiliation_status"] == "unknown"
    assert (by_role["Owner"]["rank"], by_role["Owner"]["title"]) == ("G4", "Lead")
    assert (by_role["Owner"]["node"], by_role["Owner"]["relationship"]) == ("node-1", "owns")
    assert by_role["Partner"]["actor_type"] == "organization"
    assert by_role["Partner"]["affiliation_status"] == "not_applicable"
    assert by_role["Reviewer"]["affiliation_status"] == "inferred"

    def unavailable(_body):
        """Simulate one bounded product-model transport failure."""
        raise OSError("offline")

    fallback = lw.derive_roles_and_responsibilities_via_llm(
        {"document_no": "DOC-1", "created_by": "Observed person", "owner_pu": "PU-1", "first_stage": "L"},
        transport=unavailable,
    )
    assert fallback[0]["source"] == "observed_code"


def test_judge_keeps_item_signal_when_overall_verdict_is_unparseable() -> None:
    """Retain a valid item response when an LLM verdict is not dichotomous."""
    item = {"item_id": "factor-item", "item_stem": "Evidence exists", "factor_id": "factor"}
    judged = lw.derive_dichotomous_judge_via_llm(
        {"report_id": "R-1", "slice_key": "PU-1", "document_nos": []},
        transport=lambda _body: {
            "verdict": "unclear",
            "item_responses": [{"item_id": "factor-item", "response": 1}],
        },
        items=[item],
    )
    assert judged["source"] == "unparseable"
    assert judged["verdict"] == "abstain"
    assert judged["item_responses"] == [{"item_id": "factor-item", "response": 1}]


def test_rate_limited_judge_is_an_explicit_abstention() -> None:
    """Persist gateway rate limiting as a non-null judge state."""
    item = {"item_id": "factor-item", "item_stem": "Evidence exists", "factor_id": "factor"}
    judged = lw.derive_dichotomous_judge_via_llm(
        {"report_id": "R-429", "slice_key": "PU-1", "document_nos": []},
        transport=lambda _body: {"model": "fixture", "abstention": "rate_limited"},
        items=[item],
    )
    assert judged["verdict"] == "abstain"
    assert judged["source"] == "llm_abstention"


def test_report_judge_retries_each_slice_after_bounded_failures() -> None:
    """Retry each slice independently so one transient outage cannot disable later reports."""
    slices = [
        {"report_id": f"R-{index}", "slice_key": f"PU-{index}", "document_nos": [], "title": "Fixture"}
        for index in range(4)
    ]

    attempts: dict[str, int] = {}

    def intermittent(body):
        """Fail twice per report before returning a complete live judge result."""
        report_id = body["report"]["report_id"]
        attempts[report_id] = attempts.get(report_id, 0) + 1
        if attempts[report_id] < 3:
            raise OSError("offline")
        return {
            "verdict": "pass",
            "item_responses": [
                {"item_id": item["item_id"], "response": 1}
                for item in body["items"]
            ],
        }

    scored = lw.score_period_reports(slices, [], judge_transport=intermittent)
    assert [row["judge"]["source"] for row in scored] == ["llm_judge"] * 4
    assert attempts == {f"R-{index}": 3 for index in range(4)}


def test_knowledge_graph_ignores_invalid_role_rows_and_empty_keyman_seed() -> None:
    """Keep KG ingestion resilient to malformed R&R data and unknown people."""
    graph = lw.build_knowledge_graph(
        [
            {
                "type": "document",
                "document_no": "DOC-1",
                "title_sample": "Fixture document",
                "roles_and_responsibilities": [
                    "not a mapping",
                    {"actor_type": "device", "actor_name": "Bot", "role": "Owner"},
                ],
            }
        ],
        [],
    )
    assert any(node["id"] == "kg:document:DOC-1" for node in graph["nodes"])
    assert lw.related_keyman_graph(graph, "Missing person") == {
        "person_name": "Missing person",
        "nodes": [],
        "edges": [],
        "depths": {},
    }
    hashed = lw._knowledge_id("person", "llm:Stored alias")
    hashed_graph = {"nodes": [{"id": hashed, "type": "person", "label": "Unrelated label"}], "edges": []}
    assert lw.related_keyman_graph(hashed_graph, "Stored alias")["nodes"][0]["id"] == hashed


def test_persisted_keyman_neighborhood_includes_document_evidenced_customer_edges(monkeypatch) -> None:
    """Attach customer hierarchy only when it is backed by the selected document."""
    monkeypatch.setattr(lw, "_database_table_exists", lambda *_args: True)
    monkeypatch.setattr(lw, "_database_query", lambda *_args: [{"node_id": "person:fixture"}])
    monkeypatch.setattr(
        lw,
        "load_persisted_kg_star",
        lambda *_args, **_kwargs: {
            "nodes": [{"id": "kg:document:DOC-1", "type": "document", "document_no": "DOC-1"}],
            "edges": [],
        },
    )
    monkeypatch.setattr(
        lw,
        "load_customer_master",
        lambda *_args: {
            "accounts": [
                {"account_name": "Parent", "document_nos": ["DOC-1"]},
                {"account_name": "Child", "document_nos": ["DOC-1"]},
            ],
            "edges": [{"parent": "Parent", "child": "Child"}],
        },
    )
    monkeypatch.setattr(lw, "related_keyman_graph", lambda graph, *_args, **_kwargs: graph)
    graph = lw.load_persisted_keyman_neighborhood(object(), "Fixture person")
    assert any(edge["relation"] == "customer_affiliate" for edge in graph["edges"])


def test_external_search_rejects_oversized_payload(monkeypatch) -> None:
    """Bound an external evidence response before its contents are interpreted."""
    monkeypatch.setenv("LINEAGEWEAVE_DEV_MODE", "1")
    monkeypatch.setenv("LINEAGEWEAVE_SEARXNG_URL", "http://127.0.0.1:8080")
    monkeypatch.setattr(
        lw,
        "_read_json_from_request",
        lambda *_args, **_kwargs: {"results": [{"content": "x" * 1_000_001}]},
    )
    result = lw.search_external_inference_evidence(["Organization A", "Organization B"])
    assert result["mode"] == "unavailable"
    assert result["evidence"] == []


def test_zotero_existing_lookup_handles_incomplete_and_unavailable_attachments(monkeypatch) -> None:
    """Reuse only exact parent records and verified bounded attachment evidence."""
    paper = {
        "paper_id": "fixture-paper",
        "title": "Fixture paper",
        "authors": "Fixture author",
        "year": 2026,
        "source_uri": "https://example.test/paper",
        "full_text": "Fixture text",
        "purpose": "Fixture purpose",
    }
    parent = {
        "key": "parent-key",
        "data": {"itemType": "journalArticle", "title": paper["title"], "url": paper["source_uri"]},
    }

    monkeypatch.setattr(lw, "_read_json_from_request", lambda *_args, **_kwargs: {"not": "a list"})
    assert lw._existing_zotero_method_paper("https://127.0.0.1:23119", paper, include_attachment=False) is None

    monkeypatch.setattr(
        lw,
        "_read_json_from_request",
        lambda *_args, **_kwargs: [{"data": dict(parent["data"])}],
    )
    assert lw._existing_zotero_method_paper("https://127.0.0.1:23119", paper, include_attachment=False) is None

    monkeypatch.setattr(lw, "_read_json_from_request", lambda *_args, **_kwargs: [parent])
    assert lw._existing_zotero_method_paper("https://127.0.0.1:23119", paper, include_attachment=False) == (
        "parent-key",
        None,
        None,
    )

    def unavailable_children(request, *_args, **_kwargs):
        """Return the parent but fail the child lookup."""
        if "/children" in request.full_url:
            raise urllib.error.URLError("offline")
        return [parent]

    monkeypatch.setattr(lw, "_read_json_from_request", unavailable_children)
    assert lw._existing_zotero_method_paper("https://127.0.0.1:23119", paper, include_attachment=True) is None

    expected_md5 = hashlib.md5(b"fixture").hexdigest()

    def incomplete_children(request, *_args, **_kwargs):
        """Supply malformed, invalid, and download-failing child records."""
        if "/children" not in request.full_url:
            return [parent]
        return [
            "not a mapping",
            {"key": "", "data": {"itemType": "attachment"}},
            {
                "key": "attachment-key",
                "data": {
                    "itemType": "attachment",
                    "url": paper["source_uri"],
                    "md5": expected_md5,
                },
            },
        ]

    monkeypatch.setattr(lw, "_read_json_from_request", incomplete_children)
    monkeypatch.setattr(
        lw,
        "_download_method_paper_attachment",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("download unavailable")),
    )
    assert lw._existing_zotero_method_paper("https://127.0.0.1:23119", paper, include_attachment=True) is None

    def mismatched_attachment(request, *_args, **_kwargs):
        """Return one attachment whose downloaded content no longer matches its checksum."""
        if "/children" not in request.full_url:
            return [parent]
        return [
            {
                "key": "attachment-key",
                "data": {
                    "itemType": "attachment",
                    "url": paper["source_uri"],
                    "md5": expected_md5,
                },
            }
        ]

    monkeypatch.setattr(lw, "_read_json_from_request", mismatched_attachment)
    monkeypatch.setattr(
        lw,
        "_download_method_paper_attachment",
        lambda *_args: (paper["source_uri"], b"different", "text/html"),
    )
    assert lw._existing_zotero_method_paper("https://127.0.0.1:23119", paper, include_attachment=True) is None

    monkeypatch.setattr(lw, "zotero_local_api_url", lambda: "https://127.0.0.1:23119")
    monkeypatch.setattr(
        lw,
        "_existing_zotero_method_paper",
        lambda *_args, **_kwargs: ("parent-key", "attachment-key", "verified-digest"),
    )
    stored = lw.store_oa_method_paper(paper, include_attachment=True)
    assert (stored["store_status"], stored["content_digest"], stored["attachment_status"]) == (
        "stored",
        "verified-digest",
        "stored",
    )
    monkeypatch.setattr(lw, "_existing_zotero_method_paper", lambda *_args, **_kwargs: ("parent-key", None, None))
    stored_without_attachment = lw.store_oa_method_paper(paper, include_attachment=False)
    assert (stored_without_attachment["content_digest"], stored_without_attachment["attachment_status"]) == (
        lw._paper_content_digest(paper),
        "not_attempted",
    )


def test_mutations_work_without_an_in_memory_snapshot(monkeypatch) -> None:
    """Persist authorized writes even before a local graph cache has been built."""
    application = server.LineageApplication("postgresql://fixture", "public.fixture_rows")
    actor = {"account_id": "fixture-user"}
    document = {"document_no": "DOC-1", "title_sample": "Fixture document"}
    monkeypatch.setattr(application, "document", lambda *_args: {"document": dict(document)})
    monkeypatch.setattr(application, "_flush_event_outbox", lambda: 0)
    monkeypatch.setattr(server.psycopg, "connect", lambda *_args, **_kwargs: _Connection())
    monkeypatch.setattr(lw, "apply_visibility", lambda item, visibility, _actor: {**item, "visibility": visibility})
    monkeypatch.setattr(lw, "persist_visibility", lambda *_args: None)
    monkeypatch.setattr(lw, "authorize_access", lambda **_kwargs: {"allowed": True})
    monkeypatch.setattr(lw, "ensure_keyman_override_columns", lambda *_args: None)
    monkeypatch.setattr(lw, "_database_exec", lambda *_args: None)
    monkeypatch.setattr(lw, "enqueue_event_outbox", lambda *_args: None)
    monkeypatch.setattr(lw, "persist_issue_work_items", lambda *_args: None)

    def unavailable_product_transport():
        """Force the deterministic ticket-work-item fallback."""
        raise RuntimeError("offline")

    monkeypatch.setattr(lw, "resolve_product_transport", unavailable_product_transport)
    monkeypatch.setattr(
        lw,
        "map_issue_to_work_items",
        lambda *_args: {"todo": {"title": "Fixture todo"}, "calendar": {"title": "Fixture calendar"}},
    )

    assert application.set_visibility(actor, "DOC-1", "private")["visibility"] == "private"
    assert application.set_keymen(actor, "DOC-1", {"our_side": [{"person_name": "Fixture person"}]})["our_side"]
    assert application.create_ticket(actor, "DOC-1", {"title": "Fixture ticket"})["todo"]["title"] == "Fixture todo"
    monkeypatch.setattr(lw, "resolve_keyman_transport", lambda: (lambda _body: {}, "fixture"))
    monkeypatch.setattr(
        lw,
        "derive_keymen_via_llm",
        lambda *_args, **_kwargs: {
            "our_side": [{"person_name": "Derived person"}],
            "counterpart_side": [],
            "names": ["Derived person"],
            "source": "llm",
            "status": "orchestrator",
            "orchestration": {},
        },
    )
    assert application.derive_keymen(actor, "DOC-1")["document"]["keymen"] == ["Derived person"]
    assert application._payload is None
