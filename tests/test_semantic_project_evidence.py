import pytest

from lineageweave.post_summary import (
    normalize_project_key,
    parse_project_candidate_node_id,
    parse_summary_response,
    project_candidate_node_id,
)


def test_project_mentions_keep_evidence_and_low_confidence() -> None:
    summary = parse_summary_response(
        '{"korean_summary":"synthetic summary", "project_mentions": ['
        '{"project_name":"Project Delta", "canonical_name":"Project Delta", '
        '"evidence":"the Delta rollout", "confidence":0.82}, '
        '{"project_name":"maybe", "canonical_name":"maybe", '
        '"evidence":"unclear reference", "confidence":0.4}]}'
    )

    assert summary is not None
    assert [mention.evidence for mention in summary.project_mentions] == [
        "the Delta rollout",
        "unclear reference",
    ]
    assert summary.project_mentions[1].confidence == 0.4
    assert normalize_project_key("Project Delta") == "project-delta"


def test_project_candidate_identity_is_scoped_to_its_evidence_post() -> None:
    first = project_candidate_node_id(
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1", "project-delta"
    )
    second = project_candidate_node_id(
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2", "project-delta"
    )

    assert first != second
    assert parse_project_candidate_node_id(first) == (
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
        "project-delta",
    )
    with pytest.raises(ValueError, match="separator"):
        parse_project_candidate_node_id("project-delta")
    with pytest.raises(ValueError, match="normalized"):
        project_candidate_node_id(
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1", ""
        )
