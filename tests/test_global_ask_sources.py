from __future__ import annotations

import asyncio

from backend.app.post_chat_ingestion import gather_global_chat_sources


def test_global_sources_apply_visibility_before_normalization() -> None:
    rows = [
        {
            "post_id": "public-post",
            "post_title": "Public evidence",
            "post_body": "<p>public body</p>",
            "visibility_code": "public",
            "corporate_entity_id": None,
        },
        {
            "post_id": "private-affiliated",
            "post_title": "Affiliated evidence",
            "post_body": "<p>affiliated body</p>",
            "visibility_code": "private",
            "corporate_entity_id": "corp-demo",
        },
        {
            "post_id": "private-hidden",
            "post_title": "Hidden evidence",
            "post_body": "<p>hidden body</p>",
            "visibility_code": "private",
            "corporate_entity_id": "corp-other",
        },
    ]

    class FakeConnection:
        async def fetch(self, query: str, *args):
            return rows if "from source_post" in query else []

    sources = asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda row: row["visibility_code"] == "public"
            or row["corporate_entity_id"] == "corp-demo",
            {"corp-demo"},
        )
    )

    assert [source.post_id for source in sources] == ["public-post", "private-affiliated"]
    assert sources[0].post_body == "public body"
    assert sources[1].post_body == "affiliated body"


def test_global_sources_prioritize_question_terms_and_bound_long_bodies() -> None:
    rows = [
        {
            "post_id": "newest-post",
            "post_title": "Unrelated evidence",
            "post_body": "ordinary body",
            "visibility_code": "public",
            "corporate_entity_id": None,
            "matched_in": "body",
        },
        {
            "post_id": "uam-post",
            "post_title": "UAM deployment evidence",
            "post_body": "x" * 7000,
            "visibility_code": "public",
            "corporate_entity_id": None,
            "matched_in": "title",
        },
    ]
    calls: list[tuple[str, tuple[object, ...]]] = []

    class FakeConnection:
        async def fetch(self, query: str, *args):
            calls.append((query, args))
            return rows if "from source_post" in query else []

    sources = asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda row: True,
            question="Which posts mention UAM?",
            limit=8,
        )
    )

    candidate_query, candidate_args = calls[0]
    source_query, source_args = next(
        (query, args) for query, args in calls if "array_position($2::uuid[], post_id)" in query
    )
    assert "to_tsvector('simple'" in candidate_query
    assert candidate_args[0] == "mention"
    assert "array_position($2::uuid[], post_id)" in source_query
    assert source_args[2] == 8
    # Live bug (2026-08-19): a title match must outrank a body/source-field
    # match regardless of discovery order -- "uam-post" matched in the
    # title (higher weight) but was appended to candidate_rows after
    # "newest-post" (a body match); the final candidate_ids array passed
    # as $2 must still rank uam-post first.
    assert list(source_args[1]) == ["uam-post", "newest-post"]
    assert sources[1].post_body.startswith("x" * 4000)
    assert "Source body truncated for Global Ask" in sources[1].post_body


def test_global_sources_carry_source_and_semantic_evidence() -> None:
    rows = [
        {
            "post_id": "semantic-post",
            "post_title": "Operational note",
            "post_body": "No project name in this body.",
            "visibility_code": "public",
            "corporate_entity_id": None,
            "source_project_code": "PROJECT-HINT",
            "source_record_key": "SYNTHETIC-KEY-001",
            "matched_in": "source_field",
        }
    ]

    class FakeConnection:
        async def fetch(self, query: str, *args):
            if "from source_post" in query:
                return rows
            if "from post_project_mention" in query:
                return [
                    {
                        "post_id": "semantic-post",
                        "fact": "project: semantic project | ontology_iri: urn:test",
                    }
                ]
            return []

    sources = __import__("asyncio").run(
        gather_global_chat_sources(
            FakeConnection(), lambda row: True, question="PROJECT-HINT", limit=1
        )
    )

    assert len(sources) == 1
    assert any(
        "source project code=PROJECT-HINT" in fact for fact in sources[0].evidence_facts
    )
    assert sources[0].evidence_facts[-1].startswith("project: semantic project")
