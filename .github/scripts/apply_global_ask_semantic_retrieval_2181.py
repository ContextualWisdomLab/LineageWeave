#!/usr/bin/env python3
"""Apply the one-shot Global Ask semantic candidate retrieval patch release."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent

TEST_NAME = "test_global_sources_discover_posts_from_persisted_semantic_evidence"

TEST_BLOCK = dedent(
    '''


def test_global_sources_discover_posts_from_persisted_semantic_evidence() -> None:
    """A semantic fact can nominate a post when source text cannot."""
    source_row = {
        "post_id": "semantic-only-post",
        "post_title": "Operational note",
        "post_body": "The visible source text deliberately omits the buyer term.",
        "visibility_code": "public",
        "corporate_entity_id": None,
    }
    calls: list[tuple[str, tuple[object, ...]]] = []

    class FakeConnection:
        async def fetch(self, query: str, *args):
            calls.append((query, args))
            if "semantic_candidate_matches" in query:
                return [{"post_id": "semantic-only-post"}]
            if "post_id = any($2::uuid[])" in query:
                return [source_row] if args[1] == ["semantic-only-post"] else []
            if "from post_project_mention" in query:
                return [
                    {
                        "post_id": "semantic-only-post",
                        "fact": (
                            "project: Phoenix transformation | evidence: approved "
                            "[provenance=post_project_mention]"
                        ),
                    }
                ]
            return []

    sources = asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda row: True,
            question="Who owns the Phoenix transformation?",
            limit=4,
        )
    )

    assert [source.post_id for source in sources] == ["semantic-only-post"]
    assert any(
        fact.startswith("project: Phoenix transformation")
        for fact in sources[0].evidence_facts
    )
    semantic_query = next(
        query for query, _ in calls if "semantic_candidate_matches" in query
    )
    assert "post_project_mention" in semantic_query
    assert "post_summary_role" in semantic_query
    assert "post_person_mention" in semantic_query
    assert "cataloged_person" in semantic_query
'''
)

OLD_CANDIDATE_TAIL = '''        candidate_ids.extend(str(row["post_id"]) for row in candidate_rows)
    candidate_ids = list(dict.fromkeys(candidate_ids))
'''

NEW_CANDIDATE_TAIL = '''        candidate_ids.extend(str(row["post_id"]) for row in candidate_rows)
        semantic_candidate_rows = await conn.fetch(
            """
            select post_id
              from (
                   (select mention.post_id, source.created_at
                      from post_project_mention mention
                      join source_post source on source.post_id = mention.post_id
                     where concat_ws(' ', mention.project_name,
                                      mention.evidence_text,
                                      mention.ontology_iri)
                               ilike '%' || $1 || '%'
                     limit 32)
                    union all
                   (select role.post_id, source.created_at
                      from post_summary_role role
                      join source_post source on source.post_id = role.post_id
                     where concat_ws(' ', role.actor_name,
                                      role.responsibility,
                                      role.affiliated_organization_name)
                               ilike '%' || $1 || '%'
                     limit 32)
                    union all
                   (select mention.post_id, source.created_at
                      from post_person_mention mention
                      join cataloged_person person on person.person_id = mention.person_id
                      join source_post source on source.post_id = mention.post_id
                     where concat_ws(' ', person.person_name,
                                      person.last_known_job_title,
                                      mention.mention_context)
                               ilike '%' || $1 || '%'
                     limit 32)
                   ) semantic_candidate_matches
             order by created_at desc, post_id desc
            limit 32
            """,
            term,
        )
        candidate_ids.extend(
            str(row["post_id"]) for row in semantic_candidate_rows
        )
    candidate_ids = list(dict.fromkeys(candidate_ids))
'''

CHANGELOG_ENTRY = dedent(
    '''
    ## [2.18.1] - 2026-08-20

    ### Fixed

    - Global Ask now nominates candidates from persisted project,
      role/responsibility/affiliation, and cataloged Keyman evidence in addition
      to lexical source text and raw source hints. A semantic-only buyer term can
      reach the authorized cited post without bypassing visibility or ABAC
      (ADR 0091 / ADR 0047 / ADR 0039).

    '''
)

ADR_TEXT = dedent(
    '''
    # ADR 0091: Global Ask candidates include persisted semantic evidence

    - Status: Accepted
    - Date: 2026-08-20
    - Owners: LineageWeave
    - Extends: ADR 0090 authenticated Global Ask MCP
    - Closes: the lexical-only implementation gap under ADR 0047

    ## Context

    ADR 0047 requires Global Ask to retrieve the same authorized buyer evidence
    exposed by Board: source identity, project mentions, stored roles,
    affiliations, cataloged Keymen, title, and normalized body. The shared
    assembler loaded persisted semantic facts only after a post had already
    been selected from lexical text or raw source hints.

    A buyer or authenticated MCP client could therefore see a project or owner
    in an evidence drawer, ask with that exact semantic fact, and receive no
    cited post when the words were absent from raw source text. This was a
    source-contract mismatch, not a model-quality problem.

    ## Decision

    Each bounded question term nominates candidates from both the existing
    lexical/source-hint channels and these persisted channels:

    - `post_project_mention`: project name, evidence, ontology IRI;
    - `post_summary_role`: actor, responsibility, affiliation;
    - `post_person_mention` plus `cataloged_person`: Keyman name, job title, and
      mention context.

    Candidate IDs are not evidence and grant no access. The existing authorized
    `source_post` query and application ABAC predicate still run before body,
    graph, or semantic facts enter contextual-orchestrator. Question terms,
    per-channel candidates, final sources, body length, and graph facts remain
    bounded. ADR 0090's MCP question bound and distributed rate limit remain in
    force.

    ## Consequences

    - Browser and MCP Global Ask share semantic-only candidate retrieval.
    - Hidden semantic matches remain hidden behind visibility and ABAC.
    - This does not claim embedding similarity, exhaustive recall, causal
      inference, or an answer unsupported by selected sources.

    ## Verification

    `tests/test_global_ask_sources.py` contains a regression whose title, body,
    and raw hints omit the buyer term. Persisted semantic evidence alone
    nominates the authorized source and accompanies the citation.
    '''
)

RELEASE_TEXT = dedent(
    '''
    # 2.18.1 Global Ask finds semantic-only evidence

    Browser and authenticated MCP Global Ask now find an authorized post when a
    buyer term exists only in persisted project, responsibility, affiliation,
    or Keyman evidence. The cited post still crosses the same visibility and
    ABAC boundary before any content reaches contextual-orchestrator.

    This release preserves the MCP question bound and distributed rate limit.
    It does not claim exhaustive semantic search or invent a source,
    relationship, customer, cutoff body, or TEPP result.
    '''
)

FRAGMENT_TEXT = dedent(
    '''
    # 2.18.1 — Global Ask semantic candidate retrieval

    ## Fixed

    - Browser and MCP Global Ask now nominate authorized source posts from
      persisted project, role/responsibility/affiliation, and Keyman evidence,
      not only lexical source text and raw source hints (ADR 0091).
    - Candidate nomination does not bypass the existing visibility and ABAC
      gate, MCP question bound, or distributed invocation rate limit.
    '''
)


def append_regression() -> None:
    """Append the semantic-only regression exactly once."""
    path = Path("tests/test_global_ask_sources.py")
    text = path.read_text()
    if TEST_NAME not in text:
        path.write_text(text.rstrip() + TEST_BLOCK + "\n")


def replace_once(path_name: str, old: str, new: str) -> None:
    """Replace one exact source contract, failing closed on drift."""
    path = Path(path_name)
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path_name}: expected one match, found {count}")
    path.write_text(text.replace(old, new, 1))


def apply_implementation() -> None:
    """Apply production, version, ADR, and release changes."""
    backend = Path("backend/app/post_chat_ingestion.py")
    backend_text = backend.read_text()
    if "semantic_candidate_matches" not in backend_text:
        if backend_text.count(OLD_CANDIDATE_TAIL) != 1:
            raise SystemExit("Global Ask candidate insertion point drifted")
        backend.write_text(
            backend_text.replace(OLD_CANDIDATE_TAIL, NEW_CANDIDATE_TAIL, 1)
        )

    for path_name, old, new in (
        ("pyproject.toml", 'version = "2.18.0"', 'version = "2.18.1"'),
        ("frontend/package.json", '"version": "2.18.0"', '"version": "2.18.1"'),
        ("backend/app/mcp_server.py", '_SERVER_VERSION = "2.18.0"', '_SERVER_VERSION = "2.18.1"'),
    ):
        text = Path(path_name).read_text()
        if new not in text:
            replace_once(path_name, old, new)

    changelog = Path("CHANGELOG.md")
    changelog_text = changelog.read_text()
    if "## [2.18.1] - 2026-08-20" not in changelog_text:
        marker = "## [2.17.0] - 2026-08-19\n"
        if changelog_text.count(marker) != 1:
            raise SystemExit("CHANGELOG 2.17.0 marker drifted")
        changelog.write_text(changelog_text.replace(marker, CHANGELOG_ENTRY + marker, 1))

    Path("docs/adr/0091-global-ask-semantic-candidate-retrieval.md").write_text(
        ADR_TEXT
    )
    Path("docs/releases").mkdir(parents=True, exist_ok=True)
    Path("docs/releases/2.18.1.md").write_text(RELEASE_TEXT)
    Path("CHANGELOG.d").mkdir(parents=True, exist_ok=True)
    Path("CHANGELOG.d/2.18.1-global-ask-semantic-candidate-retrieval.md").write_text(
        FRAGMENT_TEXT
    )


def main() -> None:
    """Run the requested one-shot phase."""
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("test-only", "apply"))
    args = parser.parse_args()
    append_regression()
    if args.phase == "apply":
        apply_implementation()


if __name__ == "__main__":
    main()
