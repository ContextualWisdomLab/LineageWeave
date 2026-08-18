from lineageweave.post_summary import normalize_project_key, parse_summary_response


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
